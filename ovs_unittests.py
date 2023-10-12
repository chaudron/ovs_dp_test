#!/usr/bin/env python3

"""
 Copyright 2022, Eelco Chaudron

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.

 Files name:
   ovs_unittests.py

 Description:
   This script is a front-end script to the datapath test Vagrant image.
   It requires OVS and DPDK to be checked out in the ovs and dpdk directory.

 Author:
   Eelco Chaudron

 Initial Created:
   9 June 2022

 Usage:
   This script requires Vagrant and the following python modules to be
   installed:
     pip3 install --user rich

   First install ovs and dpdk in the respective location:
     git clone https://github.com/openvswitch/ovs.git ovs
     git clone -b v22.11.1 http://dpdk.org/git/dpdk-stable dpdk

   If this is the first time you run this script, you can use it without
   any options. If not, you could skip provisioning, --skip-provision, and
   optionally skip the build phase, --skip-build.
     ./ovs_unittests.py

   For more options use the --help option.

 Example:
   See 'Usage' above.

"""

#
# Global imports
#
import argparse
import os
import re
import subprocess
import sys

from operator import itemgetter
from rich.console import Console

#
# Global defines
#
DEFAULT_VAGRANT_TARGET = 'fedora'


#
# vagrant_state()
#
def vagrant_state(target=None, vm_type=None):
    '''Get the state of a vagrant instance (running, shutoff, not_created)'''

    if target is None:
        raise ValueError("Vagrant target not set!")

    env = os.environ.copy() | {"VM_NAME": target}

    if vm_type:
        env |= {"VM_TYPE": vm_type}

    try:
        output = subprocess.check_output(['vagrant',
                                          '--machine-readable', 'status'],
                                         encoding='utf8', env=env).split("\n")
    except subprocess.CalledProcessError:
        output = ""

    for line in output:
        items = line.split(",")
        if len(items) >= 4 and items[1] == target and items[2] == 'state':
            return items[3]

    return 'UNKNOWN'


#
# vagrant_destroy()
#
def vagrant_destroy(target=None, vm_type=None):
    '''Forcefully destroy a vagrant VM'''

    if target is None:
        raise ValueError("Vagrant target not set!")

    env = os.environ.copy() | {"VM_NAME": target}

    if vm_type:
        env |= {"VM_TYPE": vm_type}

    try:
        subprocess.check_output(['vagrant',
                                 'destroy', '--force',
                                 '--machine-readable', target],
                                encoding='utf8', env=env)
    except subprocess.CalledProcessError:
        pass

    if vagrant_state(target=target, vm_type=vm_type) != 'not_created':
        return False

    return True


#
# vagrant_up()
#
def vagrant_up(console=None, target=None, vm_type=None, provision=None,
               quiet=False, cpus=4):
    '''Bring a vagrant image up'''

    if target is None:
        raise ValueError("Vagrant target not set!")

    env = os.environ.copy() | {"VM_NAME": target} | {"VM_CPUS": str(cpus)}
    if vm_type:
        env |= {"VM_TYPE": vm_type}

    arguments = ['vagrant', 'up', '--no-color']

    if provision is None:
        arguments += ['--no-provision']

    arguments += [target]

    with subprocess.Popen(arguments, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          encoding='utf8', env=env) as process:

        if console:
            with console.status(
                    f'[bold green]Bringing up VM "{target}"...') as status:
                while process.stdout.readable():
                    line = process.stdout.readline()
                    if not line:
                        break

                    if not quiet:
                        status.console.print("  " + line.strip(),
                                             highlight=False)
        else:
            while process.stdout.readable():
                line = process.stdout.readline()
                if not line:
                    break

        process.wait()

    if vagrant_state(target=target, vm_type=vm_type) != 'not_created':
        return False

    return True


#
# vagrant_provision()
#
def vagrant_provision(console=None, target=None, vm_type=None,
                      provision_with=None, quiet=False, cpus=4, env=None):
    '''Provision a running vagrant image'''

    if target is None:
        raise ValueError("Vagrant target not set!")

    cpus = str(cpus)
    arguments = ['vagrant', 'provision', '--no-color']

    if provision_with is not None and len(provision_with) > 0:
        provision = ""
        for name in provision_with:
            if len(provision) == 0:
                provision += f"{name}"
            else:
                provision += f",{name}"

        arguments += ['--provision-with'] + [provision]

    arguments += [target]

    if env is None:
        env = os.environ.copy() | {"VM_NAME": target} | {"VM_CPUS": cpus}
    else:
        env = os.environ.copy() | {"VM_NAME": target} | {"VM_CPUS": cpus} | env

    if vm_type:
        env |= {"VM_TYPE": vm_type}

    with subprocess.Popen(arguments, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, env=env,
                          encoding='utf8') as process:

        if console:
            if provision is not None:
                status_msg = f'[bold green]Provisioning VM "{target}" ' \
                             f'with "{provision}"...'
            else:
                status_msg = f'[bold green]Provisioning VM "{target}"...'

            with console.status(status_msg) as status:
                while process.stdout.readable():
                    line = process.stdout.readline()
                    if not line:
                        break

                    if not quiet:
                        status.console.print("  " + line.strip(),
                                             highlight=False)
        else:
            while process.stdout.readable():
                line = process.stdout.readline()
                if not line:
                    break

        process.wait()
        return_code = process.returncode

    if return_code != 0:
        return False

    return True


#
# cleanup_result_file()
#
def cleanup_result_file(file, target=None):
    '''Delete file if it exists'''

    if target is None:
        raise ValueError("Vagrant target not set!")

    try:
        os.remove(f"./results/{target}/{file}")
    except FileNotFoundError:
        pass


#
# process_results()
#
def process_results(file, target=None, skiplist=None):
    '''Process the result file.

    Check for errors and invalid skipped tests.
    '''
    file = (f"./results/{target}/{file}")

    if target is None:
        raise ValueError("Vagrant target not set!")

    skipped_list = []
    error_list = []
    parsing_skipped = False
    parsing_errors = False

    #
    # Read log in memory
    #
    try:
        with open(file, 'r', encoding="utf8") as in_file:
            lines = in_file.readlines()
    except (FileNotFoundError, PermissionError):
        return None, None

    for line in lines:
        line = line.rstrip('\r\n')

        if line == "## Running the tests. ##":
            parsing_skipped = True
            parsing_errors = False

        elif line == "## Summary of the failures. ##":
            parsing_errors = True
            parsing_skipped = False

        elif line in ("## Test results. ##", "Skipped tests:",
                      "## Detailed failed tests. ##"):
            parsing_skipped = False
            parsing_errors = False

        elif parsing_skipped:
            skip_regex = r'^(\d+)\. (.*) \((.+:\d+)\): skipped .+$'
            match = re.search(skip_regex, line)
            if match is not None and len(match.groups()) == 3:
                skipped_list.append([match.groups()[0],
                                     match.groups()[1],
                                     match.groups()[2]])

        elif parsing_errors:
            error_regex = r'^ *(\d+): (.+:\d+) (.+)$'
            match = re.search(error_regex, line)
            if match is not None and len(match.groups()) == 3:
                error_list.append([match.groups()[0],
                                   match.groups()[2],
                                   match.groups()[1]])

    #
    # Remove valid skipped_list items.
    #
    if skiplist is not None:
        try:
            with open(skiplist, 'r', encoding="utf8") as in_file:
                lines = in_file.readlines()
        except (FileNotFoundError, PermissionError):
            return None, None

        for line in lines:
            line = line.rstrip('\r\n')
            if line.startswith('#'):
                continue

            skipped_list[:] = (x for x in skipped_list if x[1] != line)

    #
    # Return the two lists
    #
    return error_list, skipped_list


#
# run_single_test()
#
def run_single_test(console, options, provision_list, skiplist_file, test_log):
    '''Run a single test case based on input parameters'''
    current_run = 0
    skipped_list = []
    first_run_errors = []
    vm_type = "ubuntu" if options.ubuntu else None
    testsuiteflags = options.testsuiteflags if options.testsuiteflags else ""

    #
    # Run test number of iteration until successful.
    #
    while current_run <= options.retry:
        current_run += 1

        if not options.dry_run:
            cleanup_result_file(test_log, target=options.vagrant_vm_name)

            if not vagrant_provision(target=options.vagrant_vm_name,
                                     vm_type=vm_type,
                                     console=console, quiet=options.quiet,
                                     provision_with=provision_list,
                                     cpus=options.vagrant_vm_cpus,
                                     env={"TESTSUITEFLAGS": testsuiteflags}):
                return "[bold red]ERROR[/]: Failed make check!"

        error_list, tmp_skipped_list = process_results(
            test_log, target=options.vagrant_vm_name, skiplist=skiplist_file)

        if error_list is None and tmp_skipped_list is None:
            return (f"[bold red]  ERROR: Can't open file \"{test_log}\" "
                    f"and/or \"{skiplist_file}\" for reading![/]")

        #
        # Store first run errors, so we can report a WARNING.
        #
        if current_run == 1:
            first_run_errors = error_list

        #
        # We only need to keep the first skipped_list failures.
        #
        if len(skipped_list) == 0:
            skipped_list = tmp_skipped_list

        #
        # Break if all tests are successful.
        #
        if len(error_list) == 0:
            break

        #
        # Re-run only the failed test cases
        #
        testsuiteflags = ' '.join([x[0] for x in error_list])

    #
    # Build error string
    #

    if len(error_list) < len(first_run_errors):
        failure_no = len(first_run_errors) - len(error_list)
        failures = "[bold orange_red1]  - [WARNING] " \
            f"{failure_no} errors required a rerun![/]\n"
    else:
        failures = ""

    error_list = [["FAILED"] + error for error in error_list]
    skipped_list = [["SKIPPED"] + skip for skip in skipped_list]

    for issue in sorted(error_list + skipped_list, key=itemgetter(0)):
        if issue[0] == "FAILED":
            failures += "[bold red]  - [FAILED ] " \
                f"{int(issue[1]):-4}. {issue[2]} ({issue[3]})[/]\n"
        else:
            failures += "[bold dark_orange3]  - [SKIPPED] " \
                f"{int(issue[1]):-4}. {issue[2]} ({issue[3]})[/]\n"

    return failures.rstrip('\r\n')


#
# run_afxdp()
#
def run_afxdp(console, options):
    '''Run afxdp test cases'''
    return run_single_test(console, options, ["Test: check-afxdp"],
                           "check_afxdp.skip_list",
                           "system-afxdp-testsuite.log")


#
# run_check()
#
def run_check(console, options):
    '''Run check test cases'''
    return run_single_test(console, options, ["Test: check"],
                           "check.skip_list", "testsuite.log")


#
# run_dpdk()
#
def run_dpdk(console, options):
    '''Run dpdk test cases'''
    return run_single_test(console, options, ["Test: check-dpdk"],
                           "check_dpdk.skip_list",
                           "system-dpdk-testsuite.log")


#
# run_kernel()
#
def run_kernel(console, options):
    '''Run kernel test cases'''
    return run_single_test(console, options, ["Test: check-kernel"],
                           "check_kernel.skip_list",
                           "system-kmod-testsuite.log")


#
# run_offloads()
#
def run_offloads(console, options):
    '''Run TC offload test cases'''
    return run_single_test(console, options, ["Test: check-offloads"],
                           "check_offloads.skip_list",
                           "system-offloads-testsuite.log")


#
# run_ovsdb()
#
def run_ovsdb(console, options):
    '''Run ovsdb cluster test cases'''
    return run_single_test(console, options, ["Test: check-ovsdb-cluster"],
                           "check_ovsdb_cluster.skip_list",
                           "ovsdb-cluster-testsuite.log")


#
# run_tso()
#
def run_tso(console, options):
    '''Run system TSO test cases'''
    return run_single_test(console, options, ["Test: check-system-tso"],
                           "check_system_tso.skip_list",
                           "system-tso-testsuite.log")


#
# run_userspace()
#
def run_userspace(console, options):
    '''Run userspace test cases'''
    return run_single_test(console, options, ["Test: check-system-userspace"],
                           "check_system_userspace.skip_list",
                           "system-userspace-testsuite.log")


#
# run_tests()
#
def run_tests(console, options):
    '''Run all tests in the options.run set'''

    vm_type = "ubuntu" if options.ubuntu else None
    failures = {}

    for test in options.run:
        console.log(f"[bold cyan]Starting test {test}[/]")

        results = globals()[f"run_{test}"](console, options)
        if results is None or len(results) == 0:
            console.log(f"[bold green]Finished test {test}[/]")
        else:
            console.log(results)
            failures[test] = results
            console.log(f"[bold red]Finished test {test}[/]")

    if len(failures) > 0:

        #
        # Get full test results just in case we want to review them.
        #
        console.log("[bold cyan]Start gathering test directory[/]")
        if not vagrant_provision(target=options.vagrant_vm_name,
                                 vm_type=vm_type,
                                 console=console, quiet=True,
                                 cpus=options.vagrant_vm_cpus,
                                 provision_with=["Get test directory"]):
            console.print("[bold red]ERROR[/]: Failed getting test directory!")

        console.log("[bold green]Finished gathering test directory[/]")

        console.log("[bold red]============ TESTS FAILURES ============[/]")

        for test in sorted(failures):
            console.log(f"[bold cyan]Test failures for {test}:[/]\n" +
                        failures[test])
        return False

    console.log("[bold green]============ NO FAILURES ============[/]")
    return True


#
# parse_arguments()
#
def parse_arguments():
    '''Parse command line arguments and return options'''

    test_list = ['afxdp', 'check', 'dpdk', 'kernel', 'offloads', 'ovsdb',
                 'tso', 'userspace']

    #
    # Argument parsing
    #
    parser = argparse.ArgumentParser()

    parser.add_argument("-b", "--skip-build",
                        help="Skip the DPDK and OVS build step",
                        action="store_true")
    parser.add_argument("-c", "--clean-vagrant",
                        help="Start with a clean vagrant install",
                        action="store_true")
    parser.add_argument("-D", "--debug",
                        help="Enable debugging",
                        type=int, const=0xff, default=0, nargs="?")
    parser.add_argument("-d", "--dry-run",
                        help="Run on existing log files",
                        action="store_true")
    parser.add_argument("-p", "--skip-provision",
                        help="Skip the vagrant provision step",
                        action="store_true")
    parser.add_argument("-q", "--quiet",
                        help="Be quiet, do not display console ouput",
                        action="store_true")
    parser.add_argument("-r", "--run",
                        help="List of tests to run, default all",
                        choices=test_list, default=test_list, nargs="+")
    parser.add_argument("-R", "--retry",
                        help="Retry failed test cases, default 2",
                        type=int, const=0, default=2, nargs="?")
    parser.add_argument("-s", "--skip",
                        help="List of tests to skip",
                        choices=test_list, default="none", nargs="+")
    parser.add_argument("--sanitizer",
                        help="Build with specific sanitizer enabled",
                        choices=["ubsan", "asan"], default=[], nargs="+")
    parser.add_argument("--testsuiteflags",
                        help="Initial value for the TESTSUITEFLAGS, "
                        "default=None", type=str, default=None)
    parser.add_argument("--vagrant-vm-cpus",
                        help="Number of CPUs to assign to the vm, default 4",
                        type=int, const=0, default=4, nargs="?")
    parser.add_argument("--vagrant-vm-name",
                        help="Name of the vagrant VM to use/create, "
                        f"default=\"{DEFAULT_VAGRANT_TARGET}\"",
                        type=str, default=DEFAULT_VAGRANT_TARGET)
    parser.add_argument("-u", "--ubuntu",
                        help="Use the Ubuntu VM instead of Fedora",
                        action="store_true")

    options = parser.parse_args()

    #
    # Update configuration if Ubuntu is used.
    #
    if options.ubuntu and options.vagrant_vm_name == DEFAULT_VAGRANT_TARGET:
        options.vagrant_vm_name = "ubuntu"

    #
    # Verify configuration settings
    #
    if options.clean_vagrant:
        if options.skip_provision:
            print(
                "ERROR: Can't combine --clean-vagrant with --skip-provision!")
            sys.exit(-1)

        if options.skip_build:
            print("ERROR: Can't combine --clean-vagrant with --skip-build!")
            sys.exit(-1)

    options.run = set(options.run) - set(options.skip)

    if len(options.run) == 0:
        print("ERROR: No tests to run!")
        sys.exit(-1)

    if options.retry < 0:
        print("ERROR: --retry should be zero or larger!")
        sys.exit(-1)

    return options


#
# main()
#
def main():
    '''Program main entry point'''

    #
    # Parse and verify arguments
    #
    options = parse_arguments()

    #
    # Use rich from here on for console output
    #
    console = Console(log_path=False)

    #
    # Create result directory
    #
    os.makedirs(
        f"./results/{options.vagrant_vm_name}/",
        exist_ok=True)

    #
    # Prepare the vagrant VM
    #
    vm_type = "ubuntu" if options.ubuntu else None
    state = vagrant_state(target=options.vagrant_vm_name, vm_type=vm_type)

    if options.clean_vagrant:
        if state != 'not_created':
            console.log("[bold cyan]Deleting existing VM[/]")
            if not vagrant_destroy(target=options.vagrant_vm_name,
                                   vm_type=vm_type):
                console.print("[bold red]ERROR[/]: Failed destroying VM!")
                sys.exit(-1)

            console.log("[bold green]Deleted existing VM[/]")
            state = 'not_created'

    if state != 'running':
        console.log("[bold cyan]Bringing up clean VM[/]")
        vagrant_up(target=options.vagrant_vm_name, vm_type=vm_type,
                   console=console, quiet=options.quiet,
                   cpus=options.vagrant_vm_cpus)
        console.log("[bold green]Clean VM up and running[/]")
        state = 'running'

    #
    # Do we need to provision the VM?
    #
    if not options.skip_provision:
        console.log("[bold cyan]Start provisioning the VM[/]")
        if not vagrant_provision(target=options.vagrant_vm_name,
                                 vm_type=vm_type,
                                 console=console, quiet=options.quiet,
                                 cpus=options.vagrant_vm_cpus,
                                 provision_with=["Linux Provisioning",
                                                 "Reboot new kernel"]):
            console.print("[bold red]ERROR[/]: Failed provisioning!")
            sys.exit(-1)

        console.log("[bold green]Finished provisioning the VM[/]")
    else:
        console.log("[bold dark_orange3]Skipped provisioning[/]")

    #
    # Do we need to build DPDK and OVS?
    #
    if not options.skip_build:
        extra_cflags = ""
        compiler = "gcc"

        if "ubsan" in options.sanitizer:
            extra_cflags += " -O1 -fno-omit-frame-pointer -fno-common " \
                "-fsanitize=undefined"
            compiler = "clang"
        if "asan" in options.sanitizer:
            extra_cflags += " -O1 -fno-omit-frame-pointer -fno-common " \
                "-fsanitize=address"
            compiler = "clang"

        extra_cflags = extra_cflags.split()
        extra_cflags = " ".join(sorted(set(extra_cflags),
                                       key=extra_cflags.index))

        console.log("[bold cyan]Start building OVS-DPDK[/]")
        if not vagrant_provision(target=options.vagrant_vm_name,
                                 vm_type=vm_type,
                                 console=console, quiet=options.quiet,
                                 cpus=options.vagrant_vm_cpus,
                                 provision_with=["Build dpdk",
                                                 "Build Open vSwitch"],
                                 env={"EXTRA_CFLAGS": extra_cflags,
                                      "CC": compiler}):

            console.print("[bold red]ERROR[/]: Failed building OVS-DPDK!")
            sys.exit(-1)

        console.log("[bold green]Finished building OVS-DPDK[/]")
    else:
        console.log("[bold dark_orange3]Skipped building OVS-DPDK[/]")

    #
    # Run tests
    #
    if not run_tests(console, options):
        sys.exit(os.EX_SOFTWARE)


#
# Start main() as the default entry point...
#
if __name__ == '__main__':
    main()
