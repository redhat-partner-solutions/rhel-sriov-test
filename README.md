# SR-IOV Tests for RHEL

## Test Connections

![alt text](/docs/images/SRIOV_RHEL_Test_Toplogy.jpg)


## Preconditions

A physical NIC card installed in the Device Under Test (DUT) capable of SR-IOV.  Includes BIOS settings enabling SR-IOV globally.

Two ports of the NIC under test are directly connected to the traffic generator (TrafficGen). In most of the test cases only one port is used. The second connection will be used for bonding tests.

The DUT kernal boot parameters should at least include iommu setting, e.g.:
```
intel_iommu=on iommu=pt
```

Running DPDK test will also require hugepages on the DUT. It's recommended to pre-setup hugepages on the DUT via its kernal boot parameters. Here is a sample kernal parameter setting that will enable 1G hugepages as well as iommu,
```
default_hugepagesz=1G hugepagesz=1G hugepages=16 iommu=pt intel_iommu=on
```  

If the hugepage is not defined via the kernel boot parameter, the test script will try to allocate the hugepages at run time. The allocation may fail and lead to test failure if the continous memory region is not big enough.

On some newer OS releases (first noticed on RHEL 9.2) command execution may fail due to [bracketed paste](https://en.wikipedia.org/wiki/Bracketed-paste). If failure due to `timeout` is noticed during a test's setup procedure, one should try disabling bracketed paste. This can be done at a session level or globally by adding `set enable-bracketed-paste off` to `/etc/inputrc`.


## Required Packages

On the DUT server, the following RPM packages are required,
* tmux
* nmap
* a container manager (podman or docker: The recommendation is to use podman for RHEL)

To install,
```
yum install -y tmux nmap podman
```

One special test case, SR_IOV_OVS_IPv6, requires Open vSwitch. Without Open vSwitch installed, this test case will be skipped. To install an up to date Open vSwitch, install from the source tree is recommended. Alternatively, an out of date Open vSwitch version can be installed just for the testing purpose. For example, in RHEL 8
```
yum install -y https://rdoproject.org/repos/rdo-release.rpm
yum install -y openvswitch
```

On the traffic generator server, the following RPM packages are required,
* nmap

To install,
```
yum install -y nmap
```

## Usage

The test script can be run from a third server. It will set up one ssh session to the TrafficGen and one to the DUT. The script will send commands over the ssh sessions to set up configuration or to send test traffic.

The test scripts supports both password-based and key-based ssh authentication. If the latter option is used, local user's ssh public key should be transferred to the DUT and trafficgen servers in advance.

The script will look for `tests/testbed.yaml` in order to access the TrafficGen and the DUT. Other than the ssh access information, other information such as the interfaces connecting the DUT and the TrafficGen will also be provided in this file. A template `testbed_template.yaml` is provided as a sample. One can build a local testbed.yaml from this sample file. The content of this file is explained below,

```
dut:
  host:                     # DUT ip address
  username: root            # need root access
  password:                 # root password (remove this line to use key-based ssh auth)
  pmd_cpus: "30,32,34"      # cpu list used for the testpmd
  interface:
    pf1:
      name: "ens7f0"        # first PF interface name
    pf2:
      name: "ens7f1"        # second PF interface name
    vf1:
      name: "ens7f3v0"      # first VF interface name
trafficgen:
  host:                     # TrafficGen ip address
  username: root            # need root access
  password:                 # root password
  interface:
    pf1:
      name: "ens8f0"        # first PF interface name
    pf2:
      name: "ens8f1"        # second PF interface name
```

If one chooses to run the test script from the TrafficGen, the trafficgen host will be `127.0.0.1`

Besides `tests/testbed.yaml`, the script will also look for `tests/config.yaml`. A template `config_template.yaml` is provided as a sample. In most situations, users can simply copy from this sample file into a local config.yaml. The content of this file is explained below,

```
dpdk_img: "docker.io/patrickkutch/dpdk:v21.11"  # DPDK build container image
github_tests_path:                # URL to the test directory
                                  # example: https://github.com/redhat-partner-solutions/rhel-sriov-test/tree/main/sriov/tests
tests_doc_file: 	                # test specification name under the test case directory
                                  # example: "README.md"
tests_name_field: 	              # name field in the test specification
                                  # example: "Test Case Name:"
randomly_terminate_control_core:  # the cpu core to share across testpmd sessions 
                                  # example: 2
randomly_terminate_max_vfs:       # a limit to put on the number of testpmd sessions and VFs
                                  # example: 8
randomly_terminate_test_chance:   # percentage chance to randomly terminate testpmd in test_SR_IOV_Randomly_Terminate_DPDK, from 0.0 to 1.0
                                  # example: 0.5
randomly_terminate_test_length:   # amount of time, in minutes, to run test_SR_IOV_Randomly_Terminate_DPDK
                                  # example: 10.5
container_manager:                # the container manager command to use (podman or docker)
                                  # example: podman
container_volumes:                # the volume mapping to use with the container command
                                  # example: "-v /sys:/sys -v /dev:/dev -v /lib/modules:/lib/modules"
vlan:                             # vlan tag used by the vlan tests, default is 10
mtu:                              # MTU size; if unspecified, the script will derive it
bonding_switch_delay:             # Expected bonding switch over/back delay in second, default is 1
# Below required for SR_IOV_Sanity_Performance
testpmd_img:                      # testpmd container image
testpmd_port:                     # testpmd REST port
trafficgen_img:                   # trafficgen container image
trafficgen_port:                  # trafficgen REST port
trafficgen_timeout:               # trafficgen command timeout (in minutes)
trafficgen_rx_bps_limit:          # trafficgen baseline comparison (bps)
log_performance:                  # boolean, use false to omit sanity performance test details in logs/result files (only pass or fail)
```

A current version of Python is recommended to run the tests. As of writing the minimum version to avoid warnings would be 3.7. However, the tests have been successfully run up to version 3.11, the latest active release as of writing. The same is true of pip, which should be a current version (23.0 as of writing, but this should be upgraded in the following steps).

Running the script from a python3 virtual environment is recommended (note that the Python version of your venv can differ from the default Python path, if desired). Install the required python modules,

```
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r sriov/requirements.txt
```

To run a specific test case, say SR_IOV_Permutation,

```
cd sriov/tests/
pytest -v SR_IOV_Permutation
```

Certain test cases support multiple iterations. The number of iterations can be specified using the `--iteration` option. For example, to run the test case  `SR_IOV_MultipleVFCreation_withMTU` 10 times,
```
pytest -v --iteration=10 SR_IOV_MultipleVFCreation_withMTU
```

To run a specific test case and generate an HTML report file,
```
pytest -v --html=report.html --self-contained-html SR_IOV_Permutation
```

To run a specific test case permutation and generate an HTML report file run the full path to the test permutation, for example,
```
pytest -v --html=report.html --self-contained-html SR_IOV_Permutation/test_SR_IOV_Permutation.py::test_SR_IOV_Permutation[False-False-False-off-off]
```

To run all SR-IOV test cases and generate an HTML report file,
```
pytest -v --html=report.html --self-contained-html SR*
```

After the test is completed, report.html will be generated under the current working directory.

## Test Case Description

Each test case has its own folder. Under this folder there are two files: `test_<testcase>.py` and `README.md`. The `README.md` under each test case folder contains the test case description. `test_<testcase>.py` is an reference implementation of this test case.

In order for the HTML test report to be generated properly, the test case name line should start with "Test Case Name: ", or what is defined by `tests_name_field` in the config.yaml file. The script will try to match `tests_name_field` to locate the test case name.

To satisfy the requirement of a unique identifier, semantic versioning should be observed when tagging releases. This will be used to formally reference a specific test specification. Where tags are not applicable, or in a case where a specific case has not yet been tagged, one may use the specific commit hash to reference a test case. For example, the following links are both valid references to the same test case specification:
```
https://github.com/redhat-partner-solutions/rhel-sriov-test/tree/v0.0.1/sriov/tests/SR_IOV_MultipleVFCreation_withMTU/README.md
https://github.com/redhat-partner-solutions/rhel-sriov-test/tree/85e9c78a0ea1fcf978f79f9b8402e46b6078690f/sriov/tests/SR_IOV_MultipleVFCreation_withMTU/README.md
``` 
The benefits of tagging and releases are that they allow for easy reference to/distribution of a complete test suite. When a change causes a new release, the test suite will be referenced by a new semantic version number. If one desires to run tests on a more adhoc basis, use a subset of tests, or perhaps run different versions of tests from different releases then a list of tests can be created with specific links (utilizing releases, commit hashes, or a combination of either). In order for the html test report to be generated properly, the tests should be run from the git repo, which will get either the tag or, if not tagged, the specific commit hash for a link.
This will allow for clear identification of when a test specification and reference implementation may diverge. See `CONTRIBUTING.md` for more information on test case identification.

## Common Code

The common code shared by all test cases is under the `sriov/common`.

The common code has its own test cases. The majority of the common code test cases are under the `tests/common/` folder. Pytest is used to execute these test cases. Because a valid `config.yaml` file is expected by pytest to establish ssh connections and execute these test cases, they are considered an e2e test.

A small portion of common code test cases are done using mock. These mock unit test cases are under the `sriov/common` folder, along with the common code itself. The purpose of the mock unit tests is to cover scenarios that are difficult to cover via the e2e tests. These tests must be run from the root of the repo, unless one sets the `PYTHONPATH` environment variable to include the root, in which case the mock tests may be run from another directory.

## Debug Failed Test Case

When a test case is failing, one may want to immediately stop the test run and keep the failed setup for manual debugging. This can not be achieved with the pytest `-x` option, as `-x` still allow the cleanup to happen. Instead, this can be done by using the `--skipclean` option.

For example, if some permutation in `SR_IOV_Permutation_DPDK` has failed, re-run this test case like this,
```pytest -v --skipclean SR_IOV_Permutation_DPDK```

The test execution will stop immediately without cleaning up, and one may access the DUT and the trafficgen to debug.

After the debug is complete, one has to manually clean up the setup.

## Uncommon options

The following test options are uncommon and meant to use under rare situations:
+ `--debug-execute`: debug command execution over the ssh session

