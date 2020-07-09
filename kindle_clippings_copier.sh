#!/usr/bin/env zsh

clippings_file=/media/kev/Kindle/documents/My\ Clippings.txt
destination_dir=$HOME/org/resources/kindle_clippings.txt

cd $destination_dir

if [[ -r $clippings_file ]]; then
    cp $clippings_file $destination_dir;
    git add .
    today="$(date)"
    git commit -m $today
    git push nuc mainline
else
    echo "Kindle does not seem to be mounted."
fi

cd -
