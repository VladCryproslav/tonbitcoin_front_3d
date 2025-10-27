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
    imagePath: '@/assets/gems/dao-nft.png',
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
    imagePath: '@/assets/gems/starter-pack-nft.png',
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
    price: 40,
    rarity: '4 class',
    description: 'For Energizers',
    imagePath: '@/assets/gems/jarvis-bot-4.webp',
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
    price: 40,
    rarity: '3 class',
    description: 'For Energizers',
    imagePath: '@/assets/gems/jarvis-bot-3.webp',
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
    price: 40,
    rarity: '2 class',
    description: 'For Energizers',
    imagePath: '@/assets/gems/jarvis-bot-2.webp',
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
    price: 40,
    rarity: '1 class',
    description: 'For Energizers',
    imagePath: '@/assets/gems/jarvis-bot-1.webp',
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
    price: 40,
    rarity: '1 Class',
    description: 'For Energizers',
    imagePath: '@/assets/gems/cryochamber.webp',
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
    price: 40,
    rarity: '3 class',
    description: 'For Miners',
    imagePath: '@/assets/gems/asic-manager-3.webp',
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
    price: 40,
    rarity: '2 class',
    description: 'For Miners',
    imagePath: '@/assets/gems/asic-manager-2.webp',
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
    price: 40,
    rarity: '1 class',
    description: 'For Miners',
    imagePath: '@/assets/gems/asic-manager-1.webp',
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
    price: 40,
    rarity: '2 class',
    description: 'For Miners',
    imagePath: '@/assets/gems/magnetic-ring-2.webp',
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
    price: 40,
    rarity: '1 class',
    description: 'For Miners',
    imagePath: '@/assets/gems/magnetic-ring-1.webp',
    benefits: [
      'For Miners',
      'Gh/s: 250-599',
      'Duration: Eternal'
    ]
  }
]

export { asicsSheet, gemsSheet }
export default asicsSheet
