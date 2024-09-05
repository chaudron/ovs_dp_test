#!/bin/bash
# Simple script to checkout, build and test OVS on Fedora ARM64.

SMTP="<SMTP_SERVER>"
EMAIL="<EMAIL_ADDRESS>"
DPDK_DIR=$PWD/dpdk
OVS_DIR=$PWD/ovs
LOG_FILE=$PWD/ci_run.log

set -e

# What to do on error...
on_error() {
echo "***** Send email with failure"
(echo -e "Subject: FAILED ARM64 OVS datapath run.\n\n" && \
  tail -n 50 "$LOG_FILE") | \
  msmtp --host=$SMTP -f $EMAIL $EMAIL
}
trap 'on_error' ERR


# Make sure all STDIO and STDERR go to a single file
exec > "$LOG_FILE" 2>&1


echo "***** Make sure OVN CI is not running"
retry=0
while systemctl is-active --quiet ovn-ci; do
    echo "----- Waiting for ovn-ci to stop..."
    sleep 300

    retry=$((retry+1))
    if [ $retry -ge 48 ]; then
        echo "ERROR: Failed waiting for ovn-ci for 4 hours!"
        false # Simulate failure and execute 'trap err'
    fi
done


echo "***** Delete previous checkout / build"
rm -rf "$OVS_DIR" "$DPDK_DIR"


echo "***** Checkout OVS"
git clone https://github.com/openvswitch/ovs.git "$OVS_DIR"


echo "***** Get the DPDK version for this branch from the GitHub action run yaml."
DPDK_VER=$(awk '/DPDK_VER:/ { print $2 }' "$OVS_DIR/.github/workflows/build-and-test.yml")
export DPDK_VER


echo "***** Download DPDK"
wget "https://fast.dpdk.org/rel/dpdk-$DPDK_VER.tar.xz"
DIR_NAME=$(tar -tf "dpdk-$DPDK_VER.tar.xz" | head -1 | cut -f1 -d"/")
tar --transform "s|^$DIR_NAME|$DPDK_DIR|" -Pxf "dpdk-$DPDK_VER.tar.xz"
rm "dpdk-$DPDK_VER.tar.xz"


echo "***** Setup virtenv"
python3 -m venv ovs_dp-venv
source ovs_dp-venv/bin/activate
python3 -m pip install --ignore-installed rich


echo "***** Kill the existing VM"
virsh undefine --nvram ovs_dp_test_fedora || true
vagrant destroy -f || true


echo "***** Run Datapath tests"
./ovs_unittests.py


echo "***** Done"
deactivate


echo "***** Send email with results"
(echo -e "Subject: Successful ARM64 OVS datapath run.\n\n" && \
  tail -n 10 "$LOG_FILE") | \
  msmtp --host=$SMTP -f $EMAIL $EMAIL
