import os
import re
import libcsbuild


def have_cstrace_result(cstrace):
    result = False
    if os.path.exists(cstrace):
        result = True
    return result


def raw_filter_cstrace_log(full_cstrace_log_path, filtered_cstrace_log_path):
    needless_pattern = ".*\)\s+= -1.*"
    unfinished_template = '(?P<front_cstrace>(.*)) <unfinished ...>'
    resumed_template = '.*<...(.*)resumed> (?P<back_cstrace>(.*))'
    fork_template = '.*\*\*\*pid-chid fork \) (?P<back_cstrace>(.*))'
    get_pid_pattern = "(?P<pid>([0-9]+))\s.*"

    refined_strace_dict = {}

    with open(full_cstrace_log_path, 'r', encoding='utf-8') as full_cstrace_log:
        with open(filtered_cstrace_log_path, 'w') as filtered_cstrace:
            for cstrace_log_line in full_cstrace_log:
                cstrace_log_line = cstrace_log_line.strip()

                # 공백라인이 들어오진 않지만, 테스트 가독성을 위해 처리
                if len(cstrace_log_line) == 0 or cstrace_log_line.startswith("#"):  # '#' 은 주석 라인(원래 없음)
                    continue

                m = re.match(needless_pattern, cstrace_log_line)
                if m is None:
                    p = re.match(get_pid_pattern, cstrace_log_line)

                    pid = p.group('pid')

                    q = re.match(unfinished_template, cstrace_log_line)
                    if q is not None:
                        refined_strace_dict[pid] = q.group('front_cstrace')
                        continue

                    r = re.match(resumed_template, cstrace_log_line)
                    if r is not None:
                        back_cstrace = r.group('back_cstrace')
                        front_cstrace = refined_strace_dict.get(pid)
                        del refined_strace_dict[pid]
                        full_cstrace_content = front_cstrace + back_cstrace
                        filtered_cstrace.write(full_cstrace_content+'\n')
                        continue

                    # LDH, vfork 를 통해 parent - child 관계 파악
                    r = re.match(fork_template, cstrace_log_line)
                    if r is not None:
                        back_cstrace = r.group('back_cstrace').strip().replace('= ', '')
                        chid = back_cstrace
                        filtered_cstrace.write(pid + ' ***pid-chid(' + chid + ')\n')
                        continue

                    filtered_cstrace.write(cstrace_log_line + "\n")


def filter_cstrace_log():
    full_cstrace_log_path = os.path.join(libcsbuild.get_working_dir(), 'full_cstrace.log')
    filtered_cstrace_log_path = os.path.join(libcsbuild.get_working_dir(), 'filtered_cstrace.log')

    raw_filter_cstrace_log(full_cstrace_log_path, filtered_cstrace_log_path)

    return filtered_cstrace_log_path
