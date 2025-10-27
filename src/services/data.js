const asicsSheet = [
  {
    shop: true,
    rarity: 'Common',
    name: 'ASIC S1',
    hash_rate: 100,
    measurement: 1,
    consumption: 1,
    speed: 0.25,
    price: 2,
    apr: 150,
  },
  {
    shop: true,
    rarity: 'Common',
    name: 'ASIC S3',
    hash_rate: 200,
    measurement: 1,
    consumption: 2,
    speed: 0.5,
    price: 4,
    apr: 150,
  },
  {
    shop: true,
    rarity: 'Rare',
    name: 'ASIC S5+',
    hash_rate: 400,
    measurement: 1,
    consumption: 4,
    speed: 1,
    price: 8,
    apr: 150,
  },
  {
    shop: true,
    rarity: 'Rare',
    name: 'ASIC S7+',
    hash_rate: 1000,
    measurement: 1,
    consumption: 10,
    speed: 2.5,
    price: 16,
    apr: 187.5,
  },
  {
    shop: true,
    rarity: 'Rare',
    name: 'ASIC S9+',
    hash_rate: 2500,
    measurement: 1,
    consumption: 23,
    speed: 6.25,
    price: 32,
    // new_price: 24,
    // perc: 25,
    // sale: true,
    apr: 234.4,
  },
  {
    shop: true,
    rarity: 'Epic',
    name: 'ASIC S11 XP',
    hash_rate: 6000,
    measurement: 1,
    consumption: 52,
    speed: 15,
    price: 64,
    apr: 281.3,
  },
  {
    shop: true,
    rarity: 'Epic',
    name: 'ASIC S15 XP',
    hash_rate: 15000,
    measurement: 1,
    consumption: 125,
    speed: 37.5,
    price: 128,
    apr: 351.6,
  },
  {
    shop: true,
    rarity: 'Epic',
    name: 'ASIC S17 XP',
    hash_rate: 40000,
    measurement: 1,
    consumption: 320,
    speed: 100,
    price: 256,
    apr: 468.8,
  },
  {
    shop: true,
    rarity: 'Legendary',
    name: 'ASIC S19 XP+',
    hash_rate: 100000,
    measurement: 1,
    consumption: 670,
    speed: 250,
    price: 512,
    apr: 585.9,
  },
  {
    shop: true,
    rarity: 'Legendary',
    name: 'ASIC S21 XP+',
    hash_rate: 250000,
    measurement: 1,
    consumption: 1460,
    speed: 625,
    price: 1024,
    apr: 732.4,
  },
  {
    shop: true,
    rarity: 'Mythic',
    name: 'ASIC SX ULTRA PRO',
    hash_rate: 600000,
    measurement: 1,
    consumption: 3000,
    speed: 1500,
    price: 2048,
    link: 'https://getgems.io/t2btc?filter=%7B%22ownership%22%3A%7B%22owner%22%3A%22EQDJMlSoT5-5CdCQROyN4SK_j0kMxpexF0Q3-boppeO7kcqg%22%7D%2C%22attributes%22%3A%7B%22Mining+speed%22%3A%5B%22600+Gh%2Fs%22%5D%7D%7D',
    apr: 878.9,
  },
  {
    shop: false,
    rarity: 'Special',
    name: 'ASIC S10 MAXX',
    hash_rate: 1000,
    measurement: 1,
    consumption: 80,
    speed: 5,
    price: 9999,
  },
  {
    shop: false,
    rarity: 'Special',
    name: 'ASIC S30 MAXX',
    hash_rate: 2000,
    measurement: 1,
    consumption: 160,
    speed: 10,
    price: 9999,
  },
  {
    shop: false,
    rarity: 'Special',
    name: 'ASIC S50 MAXX',
    hash_rate: 2800,
    measurement: 1,
    consumption: 224,
    speed: 15,
    price: 9999,
  },
  {
    shop: false,
    rarity: 'Special',
    name: 'ASIC S70 MAXX',
    hash_rate: 5000,
    measurement: 1,
    consumption: 400,
    speed: 25,
    price: 9999,
  },
  {
    shop: false,
    rarity: 'Special',
    name: 'ASIC S90 MAXX',
    hash_rate: 7500,
    measurement: 1,
    consumption: 480,
    speed: 40,
    price: 9999,
  },
]

// Активность акции для GEMS (можно включать/выключать)
const gemsSaleActive = true // Изменить на true для активации скидки
const gemsSalePercent = 50 // Процент скидки (например 50 = -50%)

const gemsSheet = [
  {
    shop: true,
    name: 'Buy DAO',
    type: 'DAO Owner',
    price: 960,
    rarity: 'Special',
    description: 'You buy 1% project',
    buttonColor: 'gold',
    hasGoldStroke: true,
    enableSale: false, // DAO не участвует в акции
    imagePath: '@/assets/gems/DAO_Owner.webp',
    link: 'https://getgems.io/tbtc?filter=%7B%22ownership%22%3A%7B%22owner%22%3A%22UQDJMlSoT5-5CdCQROyN4SK_j0kMxpexF0Q3-boppeO7kZdl%22%7D%2C%22attributes%22%3A%7B%22Rarity%22%3A%5B%22DAO%22%5D%7D%7D',
    benefits: [
      'You buy 1% project',
      'You get 1% revenue',
      'Vote strategic plans'
    ]
  },
  {
    shop: true,
    name: 'Buy NFT',
    type: 'Starter Pack',
    price: 99,
    rarity: 'Special',
    description: 'Nuclear power plant',
    buttonColor: 'purple',
    hasPurpleStroke: true,
    imagePath: '@/assets/gems/Starter_pack.webp',
    link: '', // Not used - uses TON payment instead
    benefits: [
      'Nuclear power plant',
      'ASIC S11 XP',
      'ASIC S15 XP',
      'And more ...'
    ]
  },
  {
    shop: true,
    name: 'Buy NFT',
    type: 'Jarvis Bot',
    price: 99,
    rarity: '4 class',
    description: 'For Energizers',
    imagePath: '@/assets/gems/Jarvis_NFT_4.webp',
    link: 'https://getgems.io/tbtc?filter=%7B%22ownership%22%3A%7B%22owner%22%3A%22UQDJMlSoT5-5CdCQROyN4SK_j0kMxpexF0Q3-boppeO7kZdl%22%7D%2C%22attributes%22%3A%7B%22Station+levels%22%3A%5B%221-2-3%22%5D%7D%7D',
    benefits: [
      'For Energizers',
      'Power plant lvl: 1-3',
      'Duration: Eternal'
    ]
  },
  {
    shop: true,
    name: 'Buy NFT',
    type: 'Jarvis Bot',
    price: 199,
    rarity: '3 class',
    description: 'For Energizers',
    imagePath: '@/assets/gems/Jarvis_NFT_3.webp',
    link: 'https://getgems.io/tbtc?filter=%7B%22ownership%22%3A%7B%22owner%22%3A%22UQDJMlSoT5-5CdCQROyN4SK_j0kMxpexF0Q3-boppeO7kZdl%22%7D%2C%22attributes%22%3A%7B%22Station+levels%22%3A%5B%224-5%22%5D%7D%7D',
    benefits: [
      'For Energizers',
      'Power plant lvl: 4-5',
      'Duration: Eternal'
    ]
  },
  {
    shop: true,
    name: 'Buy NFT',
    type: 'Jarvis Bot',
    price: 399,
    rarity: '2 class',
    description: 'For Energizers',
    imagePath: '@/assets/gems/Jarvis_NFT_2.webp',
    link: 'https://getgems.io/tbtc?filter=%7B%22ownership%22%3A%7B%22owner%22%3A%22UQDJMlSoT5-5CdCQROyN4SK_j0kMxpexF0Q3-boppeO7kZdl%22%7D%2C%22attributes%22%3A%7B%22Station+levels%22%3A%5B%226-7%22%5D%7D%7D',
    benefits: [
      'For Energizers',
      'Power plant lvl: 6-7',
      'Duration: Eternal'
    ]
  },
  {
    shop: true,
    name: 'Buy NFT',
    type: 'Jarvis Bot',
    price: 699,
    rarity: '1 class',
    description: 'For Energizers',
    imagePath: '@/assets/gems/Jarvis_NFT_1.webp',
    link: 'https://getgems.io/tbtc?filter=%7B%22ownership%22%3A%7B%22owner%22%3A%22UQDJMlSoT5-5CdCQROyN4SK_j0kMxpexF0Q3-boppeO7kZdl%22%7D%2C%22attributes%22%3A%7B%22Station+levels%22%3A%5B%228-9%22%5D%7D%7D',
    benefits: [
      'For Energizers',
      'Power plant lvl: 8-9',
      'Duration: Eternal'
    ]
  },
  {
    shop: true,
    name: 'Buy NFT',
    type: 'Cryochamber',
    price: 99,
    rarity: '1 Class',
    description: 'For Energizers',
    imagePath: '@/assets/gems/Cryo_NFT.webp',
    link: 'https://getgems.io/tbtc?filter=%7B%22ownership%22%3A%7B%22owner%22%3A%22UQDJMlSoT5-5CdCQROyN4SK_j0kMxpexF0Q3-boppeO7kZdl%22%7D%2C%22attributes%22%3A%7B%22Station+levels%22%3A%5B%22All+stations%22%5D%7D%7D',
    benefits: [
      'For Energizers',
      'Power plant lvl: 1-10',
      'Duration: Eternal'
    ]
  },
  {
    shop: true,
    name: 'Buy NFT',
    type: 'ASIC Manager',
    price: 49,
    rarity: '3 class',
    description: 'For Miners',
    imagePath: '@/assets/gems/ASIC_M_3.webp',
    link: 'https://getgems.io/tbtc?filter=%7B%22ownership%22%3A%7B%22owner%22%3A%22UQDJMlSoT5-5CdCQROyN4SK_j0kMxpexF0Q3-boppeO7kZdl%22%7D%2C%22attributes%22%3A%7B%22Mining+power%22%3A%5B%221-299+Gh%2Fs%22%5D%7D%7D',
    benefits: [
      'For Miners',
      'Gh/s: 1-299',
      'Duration: Eternal'
    ]
  },
  {
    shop: true,
    name: 'Buy NFT',
    type: 'ASIC Manager',
    price: 99,
    rarity: '2 class',
    description: 'For Miners',
    imagePath: '@/assets/gems/ASIC_M_2.webp',
    link: 'https://getgems.io/tbtc?filter=%7B%22ownership%22%3A%7B%22owner%22%3A%22UQDJMlSoT5-5CdCQROyN4SK_j0kMxpexF0Q3-boppeO7kZdl%22%7D%2C%22attributes%22%3A%7B%22Mining+power%22%3A%5B%22300-1199+Gh%2Fs%22%5D%7D%7D',
    benefits: [
      'For Miners',
      'Gh/s: 300-1199',
      'Duration: Eternal'
    ]
  },
  {
    shop: true,
    name: 'Buy NFT',
    type: 'ASIC Manager',
    price: 199,
    rarity: '1 class',
    description: 'For Miners',
    imagePath: '@/assets/gems/ASIC_M_1.webp',
    link: 'https://getgems.io/tbtc?filter=%7B%22ownership%22%3A%7B%22owner%22%3A%22UQDJMlSoT5-5CdCQROyN4SK_j0kMxpexF0Q3-boppeO7kZdl%22%7D%2C%22attributes%22%3A%7B%22Mining+power%22%3A%5B%221200%2B+Gh%2Fs%22%5D%7D%7D',
    benefits: [
      'For Miners',
      'Gh/s: 1200+',
      'Duration: Eternal'
    ]
  },
  {
    shop: true,
    name: 'Buy NFT',
    type: 'Magnetic ring',
    price: 99,
    rarity: '2 class',
    description: 'For Miners',
    imagePath: '@/assets/gems/Magnetic_2.webp',
    link: 'https://getgems.io/tbtc?filter=%7B%22ownership%22%3A%7B%22owner%22%3A%22UQDJMlSoT5-5CdCQROyN4SK_j0kMxpexF0Q3-boppeO7kZdl%22%7D%2C%22attributes%22%3A%7B%22Mining+power%22%3A%5B%221-249+Gh%2Fs%22%5D%7D%7D',
    benefits: [
      'For Miners',
      'Gh/s: 1-249',
      'Duration: Eternal'
    ]
  },
  {
    shop: true,
    name: 'Buy NFT',
    type: 'Magnetic ring',
    price: 199,
    rarity: '1 class',
    description: 'For Miners',
    imagePath: '@/assets/gems/Magnetic_1.webp',
    link: 'https://getgems.io/tbtc?filter=%7B%22ownership%22%3A%7B%22owner%22%3A%22UQDJMlSoT5-5CdCQROyN4SK_j0kMxpexF0Q3-boppeO7kZdl%22%7D%2C%22attributes%22%3A%7B%22Mining+power%22%3A%5B%22250-599+Gh%2Fs%22%5D%7D%7D',
    benefits: [
      'For Miners',
      'Gh/s: 250-599',
      'Duration: Eternal'
    ]
  }
]

// Функция расчета цены со скидкой
const getGemPrice = (originalPrice) => {
  if (!gemsSaleActive) return originalPrice
  return originalPrice * (1 - gemsSalePercent / 100)
}

export { asicsSheet, gemsSheet, gemsSaleActive, gemsSalePercent, getGemPrice }
export default asicsSheet
