const exec = require('child-process-promise').exec;
const Push = require('pushover-notifications');

const p = new Push({
    user: process.env['PUSHOVER_USER'],
    token: process.env['PUSHOVER_TOKEN'],
});

let fetchPromise = exec('git fetch');

let localRef = exec('git rev-parse HEAD').then(({ stdout }) => stdout);
let remoteRef = exec('git rev-parse origin/master').then(({ stdout }) => stdout);

const updateMessage = {
    title: "Home Assistant Updated",
    url: process.env.HOMEASSISTANT_URL,
    url_title: "Open Home Assistant"
};

fetchPromise.then(() => {
    return Promise.all([localRef, remoteRef]).then(refs => {
        console.log({refs});

        if(refs[0] !== refs[1]) {
            exec('./update.sh').then(({ stdout }) => {
                console.log(stdout);

                updateMessage.message = `Updated from ${refs[0]} to ${refs[1]}`;

                p.send(updateMessage);

                process.exit(0);
            });
        } else {
            console.log('up to date');
        }
    });
});