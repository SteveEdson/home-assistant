const exec = require('child-process-promise').exec;

let fetchPromise = exec('git fetch');

let localRef = exec('git rev-parse HEAD').then(({ stdout }) => stdout);
let remoteRef = exec('git rev-parse origin/master').then(({ stdout }) => stdout);

fetchPromise.then(() => {
    return Promise.all([localRef, remoteRef]).then(refs => {
        console.log({refs});

        if(refs[0] !== refs[1]) {
            exec('./update.sh').then(({ stdout }) => {
                console.log(stdout);
                process.exit(0);
            });
        } else {
            console.log('up to date');
        }
    });
});