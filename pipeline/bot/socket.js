import WebSocket from 'ws';

const wss = new WebSocket.Server({ port: 8080 });

wss.on('connection', function connection(ws) {
    ws.on('message', function incoming(message) {
        const msg = JSON.parse(message);
        if (msg["command"] == "swap") {
            console.log("SWAP COMMAND");
        }
    });

    ws.send('Hello! Message From Server!!');
});

console.log("wassup")