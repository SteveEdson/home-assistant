#!/usr/bin/env node

const git = require('simple-git/promise')();
const Push = require('pushover-notifications');
const exec = require('child-process-promise').exec;

const p = new Push({
    user: process.env['PUSHOVER_USER'],
    token: process.env['PUSHOVER_TOKEN'],
});

const updateMessage = {
    title: "Home Assistant Updated",
    url: process.env.HOMEASSISTANT_URL,
    url_title: "Open Home Assistant"
};

async function checkUpdates() {
    const update = await git.pull('origin', 'master', {'--no-rebase': null});
    if(update && update.summary.changes) {
        if(update.files.length === 1 && update.files[0] === 'ui-lovelace.yaml') {
            console.log('not restarting lovelace changes');
            return;
        }

        console.log('Got changes, restarting', update);

        const { stdout } = await exec('./update.sh', {
            cwd: __dirname
        });

        console.log(stdout);

        if(process.env['PUSHOVER_USER']) {
            updateMessage.message = 'Updated Home Assistant: ' + JSON.stringify(update.summary);

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
    } else {
        console.log('No changes');
    }
}

console.log('Checking for updates...');
checkUpdates();