import * as web3 from "@solana/web3.js";
import fetch from 'cross-fetch';
import { Wallet } from '@project-serum/anchor';
import bs58 from 'bs58';
import fs from 'fs';
import express from 'express'

// import { readJsonFile } from './readJsonFile.js'; // Adjust the path as necessary



// const configFile = null
// readJsonFile("/Users/lucassoffer/Documents/Develop/alafant/config.json")
//     .then(jsonData => configFile = jsonData)
//     .catch(error => console.error(error));

const app = express();
app.use(express.json());

// if (configFile['MODE'] = 'DEBUG') {
	// let account = web3.Keypair.generate();
	// let airdropSignature = await connection.requestAirdrop(
	// 	account.publicKey,
	// 	web3.LAMPORTS_PER_SOL,
	//   );
	// await connection.confirmTransaction({ signature: airdropSignature });

// } else if (configFile['MODE'] = 'PROD') {
	// }

const keyPath = (process.env.PRIVATE_KEY_DIR || '') + "/sol";
const secretKey = bs58.decode(fs.readFileSync(keyPath, 'utf8').trim());
const privateKeyBuffer = Buffer.from(secretKey, 'utf8');
let keypair = web3.Keypair.fromSecretKey(privateKeyBuffer);
const connection = new web3.Connection(web3.clusterApiUrl("mainnet-beta"));
const wallet = new Wallet(keypair);

const tokenList = await (await fetch('https://token.jup.ag/strict')).json();
const symbolMap = {};
const tokenMap = {};
const orderStatus = {};
tokenList.forEach((token) => {
	const { symbol, address } = token;
	symbolMap[symbol] = address;
	tokenMap[address] = token;
});

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function sendTransactionWithRetry(connection, transaction) {
    let attempts = 0;
    const maxAttempts = 5; // Set a maximum number of retry attempts
	let confirmation = null;
	let signature = null;
    while (attempts < maxAttempts) {
        try {
            // Fetch a new blockhash for each attempt
            const { blockhash } = await connection.getLatestBlockhash('confirmed');
            transaction.recentBlockhash = blockhash;
			transaction.sign([wallet.payer]);
            // Sign and serialize the transaction
            // Assuming the transaction is already signed by necessary signers
            const rawTransaction = transaction.serialize();

            // Send the raw transaction
            signature = await connection.sendRawTransaction(rawTransaction, {
                skipPreflight: true,
            });

            // Wait for confirmation
            confirmation = await connection.confirmTransaction(signature, 'confirmed');
            if (confirmation.value.err === null) {
                console.log('Transaction confirmed:', signature);
				return signature;
            }
        } catch (error) {
            console.error('Error sending transaction:', error);
            // Optionally, handle specific error types here
        }

        // Wait before retrying
        await sleep(500);
        attempts++;
    }
}

async function executeSwap(order) {
	const { inputTokenAddress, outputTokenAddress, swapAmount, slippageBps, orderID } = order;

	orderStatus[orderID] = 'PENDING'

	const inputToken = tokenMap[inputTokenAddress];
	const outputMint = outputTokenAddress;
	const amount = swapAmount * 10 ** inputToken.decimals;
	const quoteURL = `https://quote-api.jup.ag/v6/quote?inputMint=${inputToken.address}&outputMint=${outputMint}&amount=${amount}&slippageBps=${slippageBps}`;
	let currentQuoteURL = quoteURL;
	// Get a quote for the swap
	const quoteResponse = await (
			await fetch(currentQuoteURL)
	).json();

	const { swapTransaction } = await (
			await fetch('https://quote-api.jup.ag/v6/swap', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					// quoteResponse from /quote api
					quoteResponse,
					// user public key to be used for the swap
					userPublicKey: wallet.publicKey.toString(),
					// auto wrap and unwrap web3. default is true
					wrapAndUnwrapSol: true,
					// feeAccount is optional. Use if you want to charge a fee.  feeBps must have been passed in /quote API.
					// feeAccount: "fee_account_public_key"
				})
			})
		).json();


	// deserialize the transaction
	const swapTransactionBuf = Buffer.from(swapTransaction, 'base64');
	var transaction = web3.VersionedTransaction.deserialize(swapTransactionBuf);

	let txid = await sendTransactionWithRetry(connection, transaction);
	if (txid) {
		orderStatus[orderID] = txid;
	} else {
		orderStatus[orderID] = 'FAILED'
	}
}

app.get('/order_status', async (req, res) => {
	res.send(orderStatus);
	for (var key in orderStatus) {
		if (orderStatus[key] !== "PENDING") {
			delete orderStatus[key];
		}
	}
});

app.get('/is_alive', async (req, res) => {
	res.send("TRUE");
});

app.post('/get_balance', async (req, res) => {
	const splTokenMints = req.body;
    const balances = {};

    for (const mintAddress of splTokenMints) {
		if (mintAddress == symbolMap['SOL']) {
			const balanceInLamports = await connection.getBalance(wallet.publicKey);
			const balanceInSOL = balanceInLamports / web3.LAMPORTS_PER_SOL;
			balances[mintAddress] = balanceInSOL;
			continue;
		}

        const mintPublicKey = new web3.PublicKey(mintAddress);
        const tokenAccounts = await connection.getParsedTokenAccountsByOwner(
            wallet.publicKey,
            { mint: mintPublicKey }
        );

        let totalBalance = 0;
        for (const account of tokenAccounts.value) {
            const balance = account.account.data.parsed.info.tokenAmount.uiAmount;
            totalBalance += balance;
        }
        balances[mintAddress] = totalBalance;
    }
    res.send(balances);
})

app.post('/execute-swaps', async (req, res) => {
	const orders = req.body;
	// Validate each order and prepare for processing
	for (const order of orders) {
		const { inputTokenAddress, outputTokenAddress, swapAmount, slippageBps, orderID } = order;
		
		if (!inputTokenAddress || !outputTokenAddress || !swapAmount || !slippageBps || !orderID) {
			return res.status(400).send('Missing required parameters');
		} else if (!tokenMap[inputTokenAddress] || !tokenMap[outputTokenAddress]) {
			return res.status(400).send('Tokens not available for trade');
		}
	}
	
	// Process each order if validation is successful
	try {
		const promises = orders.map(order => {
			console.log("Starting Trade: ");
			console.log(order);
			executeSwap(order);
		});
		await Promise.all(promises);

		res.send(orderStatus);
	} catch (error) {
		console.error('Error executing swaps:', error);
		res.send(orderStatus);
	}
});

const PORT = 3000;
app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});