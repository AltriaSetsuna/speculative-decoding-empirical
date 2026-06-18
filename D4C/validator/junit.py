import os
import re
import shutil
import subprocess
import signal

def signal_handler(signum, frame):
    raise TimeoutError("Time out")

def set_timeout(seconds):
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)

def reset_timeout():
    signal.alarm(0)

def summarize_output(output, max_lines=12):
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return 'No output from defects4j test'
    interesting = [
        line for line in lines
        if re.search(r'(FAIL|ERROR|Failing tests|BUILD FAILED|Compilation failed|javac|Exception|error:)', line, re.IGNORECASE)
    ]
    selected = interesting[-max_lines:] if interesting else lines[-max_lines:]
    return ' | '.join(selected)

def defects4j_bin():
    home = os.environ.get('DEFECTS4J_HOME')
    if home:
        candidate = os.path.join(home, 'framework', 'bin', 'defects4j')
        if os.path.exists(candidate):
            return candidate
    return shutil.which('defects4j') or 'defects4j'

def defects4j_env():
    env = os.environ.copy()
    repairagent_env = env.get('REPAIRAGENT_ENV', '/home/yijiali/tools/miniconda3/envs/repairagent')
    env.setdefault('JAVA_HOME', '/home/yijiali/tools/miniconda3/envs/repairagent/lib/jvm')
    java_bin = os.path.join(env['JAVA_HOME'], 'bin')
    env['PATH'] = os.path.join(repairagent_env, 'bin') + os.pathsep + java_bin + os.pathsep + env.get('PATH', '')
    home = env.get('DEFECTS4J_HOME')
    if home:
        env['PATH'] = os.path.join(home, 'framework', 'bin') + os.pathsep + env['PATH']
    return env

def run_JUnit(bug_id, test_config=None):
    if test_config is None:
        test_config = {'time_out': 600}
        try:
            import yaml
            with open('config.yaml', 'r') as f:
                config = yaml.load(f, Loader=yaml.FullLoader)
                test_config = config.get('test_config', test_config)
        except Exception:
            pass
    if os.environ.get('D4C_TEST_TIMEOUT'):
        test_config['time_out'] = int(os.environ['D4C_TEST_TIMEOUT'])
    try:
        work_dir = os.path.join('defects4j', bug_id + '_buggy')
        timeout = int(test_config.get('time_out', 600))
        process = subprocess.Popen(
            [defects4j_bin(), 'test'],
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=defects4j_env(),
            start_new_session=True,
        )
        try:
            output, _ = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            output, _ = process.communicate()
            return False, f'Time out after {timeout}s'
        output = output.decode('utf-8')
        match = re.search(r'Failing tests:\s*\d+', output)
        if match:
            failing_test_result = match.group(0)
            return True if failing_test_result == 'Failing tests: 0' else False, failing_test_result

        summary = summarize_output(output)
        if re.search(r'compile|compilation|javac|error:', summary, re.IGNORECASE):
            return False, 'Compile failed: ' + summary
        if re.search(r'FAIL|BUILD FAILED|Exception|ERROR', summary, re.IGNORECASE):
            return False, 'Test failed: ' + summary
        return False, 'Failing tests count not found: ' + summary
    except (RuntimeError, TypeError, NameError, FileNotFoundError, TimeoutError) as e:
        print(e)
        if 'process' in locals():
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        return False, e

def class_read(java_file_path):
    try:
        with open(java_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except UnicodeDecodeError:
        with open(java_file_path, 'r', encoding='iso-8859-1') as file:  # otherwise, try 'iso-8859-1' or 'cp1252'
            content = file.read()
    return content

def class_write(java_file_path, content):
    with open(java_file_path, 'w', encoding='utf-8', errors='ignore') as outfile:
        outfile.write(content)
    outfile.close()
    
def extract_method_start_end_index(java_file_path, function_head, method_length):
    content = class_read(java_file_path)
    lines = content.split('\n')
    pattern_lines = function_head.split('\n')

    start_char_idx = content.find(function_head)
    if start_char_idx != -1:
        start_line_idx = content[:start_char_idx].count('\n')
        return [start_line_idx, start_line_idx + method_length]

    for i in range(len(lines)):
        if lines[i].split(')')[0].strip() == pattern_lines[0].strip():
            if len(pattern_lines) == 1:
                return [i, i + method_length]
            for j in range(len(pattern_lines))[1:]:
                if lines[i + j].split(')')[0].strip() != pattern_lines[j].strip():
                    break
            return [i, i + method_length]   
        
    return None
            
def replace_file(java_file_path, replace_index, fixed_method):
    content = class_read(java_file_path)
    class_lines = content.split('\n')
    fixed_method_lines = fixed_method.split('\n')
    fixed_method_lines[-1] = fixed_method_lines[-1].split('@Override')[0] # remove redundant '@Override' at the end of the method
    class_lines[replace_index[0]:replace_index[1]] = fixed_method_lines
    code = '\n'.join(class_lines)
    class_write(java_file_path, code)

def restore_file(file_path, bug_id):
    try:
        # Using git restore command to revert the file to the last commit state
        work_dir = os.path.join('defects4j', bug_id + '_buggy')
        rel_path = file_path.replace('defects4j/' + bug_id + '_buggy/', '')
        subprocess.run(['git', 'checkout', '--', rel_path], cwd=work_dir, check=False, timeout=60)
    except (RuntimeError, TypeError, NameError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"An error occurred while restoring changes to the file: {e}")
