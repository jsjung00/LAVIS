set -eux

sudo apt-get update && sudo apt-get install -y libgl1 vim openjdk-11-jre

uv venv --python=3.8

source /flow/.venv/bin/activate

DATA_TGZ_FILE="/scratch/lten.tgz"

if [ -f "$DATA_TGZ_FILE" ]; then
if [ ! -d "$DIR" ]; then
  echo "Error: Directory $DIR does not exist." >&2
  exit 1
fi

#tar -zxvf /scratch/lfull.tgz -C /flow/LAVIS
tar -zxvf /scratch/lten.tgz -C /flow/LAVIS_10


echo "------ INITIALIZATION IS DONE --------"
