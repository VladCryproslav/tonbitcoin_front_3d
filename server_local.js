import 'dotenv/config'
import cors from 'cors'
import express from 'express'
import path from 'path'
import fs from 'fs'
import https from 'https';

const __dirname = path.resolve()
const privateKey  = fs.readFileSync('localhost-key.pem', 'utf8');
const certificate = fs.readFileSync('localhost.pem', 'utf8');

const credentials = {key: privateKey, cert: certificate};
const app = express()

app.use(cors())
app.use(express.static(path.join(__dirname, 'dist'))) // Вказуємо правильний шлях до статичних файлів

app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'))
})

const httpsServer = https.createServer(credentials, app);

httpsServer.listen(5173);
