import * as web3 from "@solana/web3.js";

// Create connection
let connection = new web3.Connection(web3.clusterApiUrl("devnet"), "confirmed");

// Generate accounts
let account = web3.Keypair.generate();
let nonceAccount = web3.Keypair.generate();

// Fund account
let airdropSignature = await connection.requestAirdrop(
  account.publicKey,
  web3.LAMPORTS_PER_SOL,
);

await connection.confirmTransaction({ signature: airdropSignature });

// Get Minimum amount for rent exemption
let minimumAmount = await connection.getMinimumBalanceForRentExemption(
  web3.NONCE_ACCOUNT_LENGTH,
);

// Form CreateNonceAccount transaction
let transaction = new web3.Transaction().add(
  web3.SystemProgram.createNonceAccount({
    fromPubkey: account.publicKey,
    noncePubkey: nonceAccount.publicKey,
    authorizedPubkey: account.publicKey,
    lamports: minimumAmount,
  }),
);
// Create Nonce Account
await web3.sendAndConfirmTransaction(connection, transaction, [
  account,
  nonceAccount,
]);

let nonceAccountData = await connection.getNonce(
  nonceAccount.publicKey,
  "confirmed",
);

console.log(nonceAccountData);
// NonceAccount {
//   authorizedPubkey: PublicKey {
//     _bn: <BN: 919981a5497e8f85c805547439ae59f607ea625b86b1138ea6e41a68ab8ee038>
//   },
//   nonce: '93zGZbhMmReyz4YHXjt2gHsvu5tjARsyukxD4xnaWaBq',
//   feeCalculator: { lamportsPerSignature: 5000 }
// }

let nonceAccountInfo = await connection.getAccountInfo(
  nonceAccount.publicKey,
  "confirmed",
);

let nonceAccountFromInfo = web3.NonceAccount.fromAccountData(
  nonceAccountInfo.data,
);
let payerBalance = await connection.getBalance(account.publicKey);
let nonceBalance = await connection.getBalance(nonceAccount.publicKey);
console.log(nonceAccountFromInfo);
// NonceAccount {
//   authorizedPubkey: PublicKey {
//     _bn: <BN: 919981a5497e8f85c805547439ae59f607ea625b86b1138ea6e41a68ab8ee038>
//   },
//   nonce: '93zGZbhMmReyz4YHXjt2gHsvu5tjARsyukxD4xnaWaBq',
//   feeCalculator: { lamportsPerSignature: 5000 }
// }