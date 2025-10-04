#!/bin/bash
# Credit: https://cloud.google.com/compute/docs/disks/benchmarking-pd-performance

TEST_DIR=$1
mkdir -p $TEST_DIR

# Test write throughput by performing sequential writes with multiple parallel streams (8+), using an I/O block size of 1 MB and an I/O depth of at least 64:
fio \
  --name=write_throughput \
  --directory=$TEST_DIR \
  --numjobs=4 \
  --size=100M \
  --time_based \
  --runtime=60s \
  --ramp_time=2s \
  --ioengine=libaio \
  --direct=1 \
  --verify=0 \
  --bs=1M \
  --iodepth=64 \
  --rw=write \
  --group_reporting=1
# Clean up
rm -f $TEST_DIR/write* $TEST_DIR/read*

# Test write IOPS by performing random writes, using an I/O block size of 4 KB and an I/O depth of at least 64:
fio \
  --name=write_iops \
  --directory=$TEST_DIR \
  --size=100M \
  --time_based \
  --runtime=60s \
  --ramp_time=2s \
  --ioengine=libaio \
  --direct=1 \
  --verify=0 \
  --bs=4K \
  --iodepth=64 \
  --rw=randwrite \
  --group_reporting=1
# Clean up
rm -f $TEST_DIR/write* $TEST_DIR/read*

# Test read throughput by performing sequential reads with multiple parallel streams (8+), using an I/O block size of 1 MB and an I/O depth of at least 64:
fio \
  --name=read_throughput \
  --directory=$TEST_DIR \
  --numjobs=4 \
  --size=100M \
  --time_based \
  --runtime=60s \
  --ramp_time=2s \
  --ioengine=libaio \
  --direct=1 \
  --verify=0 \
  --bs=1M \
  --iodepth=64 \
  --rw=read \
  --group_reporting=1
# Clean up
rm -f $TEST_DIR/write* $TEST_DIR/read*

# Test read IOPS by performing random reads, using an I/O block size of 4 KB and an I/O depth of at least 64:
fio \
  --name=read_iops \
  --directory=$TEST_DIR \
  --size=100M \
  --time_based \
  --runtime=60s \
  --ramp_time=2s \
  --ioengine=libaio \
  --direct=1 \
  --verify=0 \
  --bs=4K \
  --iodepth=64 \
  --rw=randread \
  --group_reporting=1

# Clean up
rm -f $TEST_DIR/write* $TEST_DIR/read*