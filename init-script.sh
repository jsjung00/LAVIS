set -eux

sudo apt-get update && sudo apt-get install -y libgl1 vim openjdk-11-jre

uv venv --python=3.8

source /work/.venv/bin/activate

uv pip install -e .

#DATA_TGZ_FILE="/scratch/lfull.tgz"

#if [ ! -f "$DATA_TGZ_FILE" ]; then
#  echo "Error: file $DATA_TGZ_FILE does not exist." >&2
#  exit 1
#fi

#tar -zxvf /scratch/lfull.tgz -C /flow/
#tar -zxvf /scratch/lten.tgz -C /flow/

echo "------ INITIALIZATION IS DONE --------"