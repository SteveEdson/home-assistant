#!/usr/bin/env node

const exec = require('child-process-promise').exec;
const Push = require('pushover-notifications');

console.log('env', {
    user: process.env['PUSHOVER_USER'],
    token: process.env['PUSHOVER_TOKEN'],
    url: process.env.HOMEASSISTANT_URL,
});

const p = new Push({
    user: process.env['PUSHOVER_USER'],
    token: process.env['PUSHOVER_TOKEN'],
});

let fetchPromise = exec('git fetch --verbose', {
   cwd: __dirname
});

let localRef = exec('git rev-parse HEAD', {
   cwd: __dirname
}).then(({ stdout }) => stdout);

const updateMessage = {
    title: "Home Assistant Updated",
    url: process.env.HOMEASSISTANT_URL,
    url_title: "Open Home Assistant"
};

fetchPromise.then(({ stdout }) => {
    let remoteRef = exec('git rev-parse origin/master', {
        cwd: __dirname
    }).then(({ stdout }) => stdout);

    console.log('fetch', stdout);
    return Promise.all([localRef, remoteRef]).then(refs => {
        console.log({refs});

        if(refs[0] !== refs[1]) {

            console.log('running update');

            exec('./update.sh', {
               cwd: __dirname
            }).then(({ stdout }) => {
                console.log('update result', stdout);

                updateMessage.message = `Updated from ${refs[0]} to ${refs[1]}`;

                if(process.env['PUSHOVER_USER']) {
                    console.log('sending', updateMessage);

                    p.send(updateMessage, function (err, result) {
                        if (err) {
                            console.error(err);
                            throw err;
                        }

                        console.log('pushover', result);

                        process.exit(0);
                    });
                } else {
                    process.exit(0);
                }
            });
        } else {
            console.log('up to date');
        }
    });
});
