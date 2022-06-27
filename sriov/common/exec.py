from ast import Pass
from logging import Logger
import paramiko
import re
import signal


class ShellHandler:

    def __init__(self, host, user, psw):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(host, username=user, password=psw, port=22)

        channel = self.ssh.invoke_shell()
        self.stdin = channel.makefile('wb')
        self.stdout = channel.makefile('r')

    def __del__(self):
        try:
            if self.testpmd_active():
                self.stop_testpmd()
        except Exception:
            pass
        self.ssh.close()

    @staticmethod
    def timeout_handler(signum, frame):
        raise Exception("timeout")
        
    def start_testpmd(self, cmd):
        """
        :param cmd: the command to be executed on the remote computer to start the testpmd
        :example: podman run -it --rm --privileged patrickkutch/dpdk:v21.11 dpdk-testpmd
        """
        cmd = cmd.strip("\n")
        self.stdin.write(cmd + '\n')
        self.stdin.write('\n')
        finish = 'testpmd>'
        self.stdin.flush()
        
        shout = []
        sherr = []
        exit_status = 0
        signal.signal(signal.SIGALRM, self.timeout_handler)
        signal.alarm(30)
        try:
            for line in self.stdout:
                if str(line).startswith(cmd):
                    shout = []
                elif str(line).startswith(finish):
                    break
                else:
                    shout.append(re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]').sub('', line).
                             replace('\b', '').replace('\r', ''))
        except Exception as err:
            exit_status = -1
            sherr.append(str(err))    
        finally:
            signal.alarm(0)
                    
        return exit_status, shout, sherr    
             
    def testpmd_active(self):
        """
        check testpmd session is active by sending new line
        """
        self.stdin.write('\n')
        self.stdin.flush()
        finish = 'testpmd>'
        active = True
        signal.signal(signal.SIGALRM, self.timeout_handler)
        signal.alarm(1)
        try:
            for line in self.stdout:
               if str(line).startswith(finish):
                   break
        except Exception:
            active = False
        finally:
            signal.alarm(0)
        return active
    
    def stop_testpmd(self):
        """
        stop testpmd if the ssh session has a testpmd running
        """
        if not self.testpmd_active:
            return
        self.stdin.write('quit\n')
        finish = 'Bye...'
        self.stdin.flush()
        
        exit_status = 0
        signal.signal(signal.SIGALRM, self.timeout_handler)
        signal.alarm(10)
        try:
            for line in self.stdout:
                print(line)
                if str(line).startswith(finish):
                    break
        except Exception as err:
            exit_status = -1
        finally:
            signal.alarm(0)

        return exit_status
        
                          
    def execute(self, cmd):
        """
        :param cmd: the command to be executed on the remote computer
        """
        cmd = cmd.strip('\n')
        self.stdin.write(cmd + '\n')
        finish = 'end of stdOUT buffer. finished with exit status'
        echo_cmd = 'echo {} $?'.format(finish)
        self.stdin.write(echo_cmd + '\n')
        self.stdin.flush()

        shout = []
        sherr = []
        exit_status = 0
        signal.signal(signal.SIGALRM, self.timeout_handler)
        signal.alarm(5)
        try:
            for line in self.stdout:
                if str(line).startswith(cmd) or str(line).startswith(echo_cmd):
                # up for now filled with shell junk from stdin
                    shout = []
                elif str(line).startswith(finish):
                # our finish command ends with the exit status
                    exit_status = int(str(line).rsplit(maxsplit=1)[1])
                    if exit_status:
                        # stderr is combined with stdout.
                        # thus, swap sherr with shout in a case of failure.
                        sherr = shout
                        shout = []
                    break
                else:
                    # get rid of 'coloring and formatting' special characters
                    shout.append(re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]').sub('', line).
                                 replace('\b', '').replace('\r', ''))
        except Exception as err:
            exit_status = -1
            sherr.append(str(err))    
        finally:
            signal.alarm(0)

        # first and last lines of shout/sherr contain a prompt
        if shout and echo_cmd in shout[-1]:
            shout.pop()
        if shout and cmd in shout[0]:
            shout.pop(0)
        if sherr and echo_cmd in sherr[-1]:
            sherr.pop()
        if sherr and cmd in sherr[0]:
            sherr.pop(0)

        return exit_status, shout, sherr

