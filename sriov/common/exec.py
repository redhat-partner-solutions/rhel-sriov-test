from ast import Pass
from logging import Logger
import paramiko
import re
import signal
import time
from typing import *

class ShellHandler:

    def __init__(self, host: str, user: str, psw: str) -> None:
        """ Initialize the shell handler object

        Args:
            self:       self
            host (str): the SSH IP address or hostname
            user (str): the SSH username
            psw (str):  the SSH password
        """ 
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(host, username=user, password=psw, port=22)

        channel = self.ssh.invoke_shell()
        self.stdin = channel.makefile('wb')
        self.stdout = channel.makefile('r')

    def __del__(self) -> None:
        """ Delete the shell handler ssh object

        Args:
            self: self
        """
        try:
            if self.testpmd_active():
                self.stop_testpmd()
        except Exception:
            pass
        self.ssh.close()

    @staticmethod
    def timeout_handler(signum, frame) -> None:
        """ Handle the timeout by raising an exception

        Args:
            signum (signum obj): signal number
            frame (frame obj):   current stack frame

        Raises:
            Exception: timeout
        """
        raise Exception("timeout")
        
    def start_testpmd(self, cmd: str) -> Tuple[int, list, list]:
        """ Start the TestPMD application

        Args:
            self: self
            cmd (str): the command to be executed on the remote computer to
                       start the testpmd
                       example: podman run -it --rm --privileged patrickkutch/dpdk:v21.11 dpdk-testpmd

        Returns:
            exit_status (int): the exit status (0 on success, non-zero otherwise)
            shout (list):      list of stdout lines
            sherr (list):      list of stderr lines
        """
        cmd = cmd.strip("\n")
        print(cmd)
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
             
    def testpmd_active(self) -> bool:
        """ A test of activity for the TestPMD session by sending a newline 
            heartbeat

        Args:
            self: self

        Returns:
            active (boolean): True if TestPMD prompt exists, False otherwise 
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
    
    def stop_testpmd(self) -> int:
        """ Stop TestPMD if the SSH session has the TestPMD application running 

        Args:
            self: self

        Returns:
            exit_status (int): the exit status (0 on success, non-zero otherwise)
        """
        if not self.testpmd_active():
            return 0
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
        # sleep before return
        time.sleep(1)
        return exit_status
       
    def testpmd_cmd(self, cmd: str) -> int:
        """ Send a command to the TestPMD application 

        Args:
            self:      self
            cmd (str): the command to be executed in the TestPMD session

        Returns:
            exit_code (int): the exit status (0 on success, non-zero otherwise)

        Raises:
            Exception: TestPMD not active
        """
        if not self.testpmd_active():
            raise Exception('TestPMD not active')
        cmd = cmd.strip('\n')
        self.stdin.write(cmd + '\n')
        self.stdin.flush()
        finish = 'testpmd>'
        signal.signal(signal.SIGALRM, self.timeout_handler)
        signal.alarm(1)
        exit_code = 0
        try:
            for line in self.stdout:
               if str(line).startswith(finish):
                   break
        except Exception:
            exit_code = -1
        finally:
            signal.alarm(0)
            
        return exit_code
                                  
    def execute(self, cmd: str, timeout: int = 5) -> Tuple[int, list, list]:
        """ Execute a command in the SSH session 

        Args:
            self:          self
            cmd (str):     the command to execute over SSH
            timeout (int): timeout for command to run (default 5)

        Returns:
            exit_status (int): the exit status (0 on success, non-zero otherwise) 
            shout (list):      list of stdout lines
            sherr (list):      list of stderr lines
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
        signal.alarm(timeout)
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

