apk update

apk fetch --no-cache docker

find . -name "docker-*.apk" | xargs -I {} sh -c 'mv "{}" docker.apk'
