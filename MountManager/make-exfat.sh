#!/bin/sh
cat /proc/filesystems | grep exfat > /dev/null 2>&1
if [ "$?" = "1" ] ; then
	cat /etc/filesystems | grep exfat > /dev/null 2>&1
	if [ "$?" = "1" ] ; then
		echo exfat-fuse >> /etc/filesystems
		echo "adding support filesystem exfat"
	fi
fi
