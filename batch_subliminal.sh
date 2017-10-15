loc=$1
#checks if user entered anything at all
if [ -z "$loc" ]
then
  echo "Missing location path!!!!!!!!"
  echo "example:"
  echo "./batch_subliminal.sh /home/user/media/"
  exit 1
else
  echo $loc "passed"
fi

cd $loc

ls -1a |grep -v srt > found.media
sed 1d found.media > found.media2
sed 1d found.media2 > found.media

IFS=$'\n'
for x in `cat found.media`
 do
        subliminal download -l en "'"${x}"'"
 done

rm -rf found.media2
rm -rf found.media
