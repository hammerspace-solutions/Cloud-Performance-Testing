#!/bin/bash
source config
# Global Parameters
RUNTIME=30
ITERATIONS=1
IPS=$client_ips
LSS_IPS=$lss_ips
BASENAME="$name"  #TODO get real name from config
SLEEPTIME=5
IOENGINE='libaio'
TESTDIR='/mnt/hs_test'
CREATE_FILES_MAX_THREADS=32
WHAT_IF=false
RUN_FIO_PATH=''  # Override with full path if needed
FIO_RESULTS_DIR='fio_results'  # Override if results dir is elsewhere
mkdir -p ${FIO_RESULTS_DIR}

# Handle arguments
while [[ "$#" -gt 0 ]]; do
  case $1 in
    -n|--what-if)
      WHAT_IF=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Resolve defaults if not set
if [[ -n "$RUN_FIO_PATH" && -f "$RUN_FIO_PATH" ]]; then
  :  # use override
elif [[ -f "./run_fio.py" ]]; then
  RUN_FIO_PATH="./run_fio.py"
else
  echo "Error: run_fio.py not found in override path or current directory."
  exit 1
fi

if [[ -n "$FIO_RESULTS_DIR" && -d "$FIO_RESULTS_DIR" ]]; then
  :  # use override
elif [[ -d "./fio_results" ]]; then
  FIO_RESULTS_DIR="./fio_results"
else
  echo "Error: fio_results directory not found in override path or current directory."
  exit 1
fi

echo "Using run_fio.py: $RUN_FIO_PATH"
echo "Using results directory: $FIO_RESULTS_DIR"

# Prerequisite checks
if ! command -v fio &> /dev/null; then
  echo "Error: 'fio' is not installed or not in PATH."
  exit 1
fi

if [[ -z "$IPS" ]]; then
  echo "Error: IPS variable is empty. Please define target hosts."
  exit 1
fi

# Parameter Sets
#BW_BLOCK_SIZES='256k 512k 1m'
BW_BLOCK_SIZES='1m'
BW_THREAD_COUNTS='1 2'
BW_QUEUE_DEPTHS='1 2'
BW_IOTYPES='JonBWWrite JonBWRead '
#BW_IOTYPES='JonBWWrite JonBWRead JonBWMix'
BW_FILE_SIZE='5G'
BW_FILE_COUNT='48' # Per Client

#IOPS_BLOCK_SIZES='4k 8k'
IOPS_BLOCK_SIZES='4k'
IOPS_THREAD_COUNTS='1 2'
IOPS_QUEUE_DEPTHS='4 8'
#IOPS_IOTYPES='JonIOPSWrite JonIOPSRead JonIOPSMix'
IOPS_IOTYPES='JonIOPSWrite JonIOPSRead '
IOPS_FILE_SIZE='4G'
IOPS_FILE_COUNT='48 96'

#SINGLE_BLOCK_SIZES='4k 1m'
SINGLE_BLOCK_SIZES='1m'
SINGLE_IOTYPES='JonIOPSRead JonIOPSWrite JonBWRead JonBWWrite'
SINGLE_FILE_SIZE='2G'

run_tests() {
  local BLOCK_SIZES="$1"
  local THREAD_COUNTS="$2"
  local QUEUE_DEPTHS="$3"
  local IOTYPES="$4"
  local FILE_SIZE="$5"
  local FILE_COUNTS="$6"
  local MODE="$7"

  local total=$(( \
    $(wc -w <<< "$THREAD_COUNTS") * \
    $(wc -w <<< "$QUEUE_DEPTHS") * \
    $(wc -w <<< "$BLOCK_SIZES") * \
    $(wc -w <<< "$FILE_COUNTS") * \
    $(wc -w <<< "$IOTYPES") * \
    $ITERATIONS \
  ))

  local count=0
  for nj in $THREAD_COUNTS; do
    for qd in $QUEUE_DEPTHS; do
      for bs in $BLOCK_SIZES; do
        for fc in $FILE_COUNTS; do
          for iotype in $IOTYPES; do
            for ((itr=1; itr<=ITERATIONS; itr++)); do
              ((count++))
              echo "Starting $MODE Test: $count out of $total"

              CMD="$RUN_FIO_PATH -N \"${BASENAME}_${MODE}_${iotype}_i${itr}_b${bs}_nj${nj}_qd${qd}_n${fc}\" -r \"$RUNTIME\" -T \"$iotype\" --ips $IPS -b $bs -s $FILE_SIZE -j $nj -q $qd -n $fc -i $IOENGINE -t $TESTDIR -o $FIO_RESULTS_DIR "

              if [[ "$itr" -eq 1 ]]; then
                if [[ $fc -gt $CREATE_FILES_MAX_THREADS ]]; then
                  CMD+=" -F $CREATE_FILES_MAX_THREADS"
                else
                  CMD+=" -F $fc"
                fi
              else
                CMD+=" -S"
              fi

              echo "$CMD"
              if $WHAT_IF; then
                for ip in $LSS_IPS $IPS; do
                  echo ssh $ip 'sudo su -; echo 3 > /proc/sys/vm/drop_caches'
                done
              else
                sleep $SLEEPTIME
                eval $CMD
#                for ip in $LSS_IPS $IPS; do
#                  ssh $ip 'sudo su -;echo 3 > /proc/sys/vm/drop_caches'
#                done
              fi
            done
          done
        done
      done
    done
  done
  echo "Completed ${MODE} Tests"
}

# Run Test Sections
run_tests "$BW_BLOCK_SIZES" "$BW_THREAD_COUNTS" "$BW_QUEUE_DEPTHS" "$BW_IOTYPES" "$BW_FILE_SIZE" "$BW_FILE_COUNT" "BW"
#run_tests "$IOPS_BLOCK_SIZES" "$IOPS_THREAD_COUNTS" "$IOPS_QUEUE_DEPTHS" "$IOPS_IOTYPES" "$IOPS_FILE_SIZE" "$IOPS_FILE_COUNT" "IOPS"
#run_tests "$SINGLE_BLOCK_SIZES" "1" "1" "$SINGLE_IOTYPES" "$SINGLE_FILE_SIZE" "1" "SINGLE"

