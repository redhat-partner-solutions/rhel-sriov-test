# SR-IOV Tests for RHEL

## Test Connections

![alt text](/docs/images/SRIOV_RHEL_Test_Toplogy.jpg)


## Preconditions

A physical NIC card installed in the Device Under Test (DUT) capable of SR-IOV.  Includes BIOS settings enabling SR-IOV globally.

Two ports of the NIC under test are directly connected to the traffic generator (TrafficGen). In most of the test cases only one port is used. The second connection will be used for bonding tests.

## Required Packages

On the DUT server, the following RPM packages are required,
* tmux
* nmap

To install,
```
yum install -y tmux nmap
```

On the traffic generator server, the following RPM packages are required,
* nmap

To install,
```
yum install -y nmap
```

## Usage

The test script can be run from a third server. It will set up one ssh session to the TrafficGen and one to the DUT. The script will send commands over the ssh sessions to set up configuration or to send test traffic.

The script will look for `tests/config.yaml` in order to access the TrafficGen and the DUT. Other than the ssh access information, other information such as the interfaces connecting the DUT and the TrafficGen will also be provided in this file. A template `config_template.yaml` is provided as a sample. One can build a local config.yaml from this sample file.

```
dpdk_img: "docker.io/patrickkutch/dpdk:v21.11"
github_tests_path:          # URL to the test directory
                            # example: https://github.com/redhat-partner-solutions/intel-sriov-test/tree/main/sriov/tests
tests_doc_file: 	          # test specification name under the test case directory
                            # example: "README.md"
tests_name_field: 	        # name field in the test specification
                            # example: "Test Case Name:"
dut:
  host:                     # DUT ip address
  username: root            # need root access
  password:                 # root password
  pmd_cpus: "30,32,34"      # cpu list used for the testpmd
  interface:
    pf1:
      name: "ens7f3"        # first PF interface name 
      pci: "0000:ca:00.3"   # first PF PCI address
    vf1:
      name: "ens7f3v0"      # first VF interface name 
      pci: "0000:ca:19.0"   # first VF PCI address
trafficgen:
  host:                     # TrafficGen ip address
  username: root            # need root access
  password:                 # root password
  interface:
    pf1:
      name: "ens8f0"        # first PF interface name
      mac: "xx:xx:xx..."    # first PF mac address
```

One may also choose to run the test script from the TrafficGen. In that case, the host will be `127.0.0.1`

Running the script from a python3 virtual enviroment is recommended. Install the required python modules,

```
python3 -m venv venv
source venv/bin/activate
pip install -r sriov/requirements.txt
```

To run a specific test case, say SR_IOV_Permutation,

```
cd sriov/tests/
pytest -v SR_IOV_Permutation
```

Certain test cases support multiple iterations of run. The number of interations can be specified using `--iteration` option. For example, to run the test case  `SR_IOV_MultipleVFCreation_withMTU` 10 times,
```
pytest -v --iteration=10 SR_IOV_MultipleVFCreation_withMTU
```

To run a specific test case and generate an HTML report file,
```
pytest -v --html=report.html --self-contained-html SR_IOV_Permutation
```

To run all SR-IOV test cases and generate an HTML report file,
```
pytest -v --html=report.html --self-contained-html SR*
```

After the test is completed, report.html will be generated under the current working directory.

## Test Case Description

Each test case has its own folder. Under this folder there are two files: `test_<testcase>.py` and `README.md`. The `README.md` under each test case folder contains the test case description. `test_<testcase>.py` is an reference implementation of this test case.

In order for the html test reported generated properly, the test case name line should start with "Test Case Name: ", or what is defined by `tests_name_field` in the config.yaml file. The script will try to match `tests_name_field` to locate the test case name.
