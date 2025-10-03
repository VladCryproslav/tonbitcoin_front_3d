import 'dotenv/config'
import cors from 'cors'
import express from 'express'
import path from 'path'

const __dirname = path.resolve() // Додаємо цю лінію для отримання __dirname

const app = express()

app.use(cors())
app.use(express.static(path.join(__dirname, 'dist'))) // Вказуємо правильний шлях до статичних файлів

app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'))
})

const PORT = process.env.PORT || 80 // Використовуємо змінну середовища для порту або 80 за замовчуванням

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`) // Виводимо правильний порт
})
