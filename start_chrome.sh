function local() {
    /Applications/Google Chrome.app/Contents/MacOS/Google Chrome --disable-gpu --headless --mute-audio --hide-scrollbars --enable-automation --disable-sync --no-first-run --remote-debugging-address='127.0.0.1' --remote-debugging-port=9222
}

function docker() {
    docker run -d -p 9222:9222 --rm --name headless-shell --shm-size 2G chromedp/headless-shell
}


docker();