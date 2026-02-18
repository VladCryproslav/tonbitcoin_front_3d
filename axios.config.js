import { useTelegram } from '@/services/telegram'
import axios from 'axios'

const { initData } = useTelegram()

function getCookie(name) {
var cookieValue = null;
if (document.cookie && document.cookie != '') {
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
        var cookie = cookies[i].trim()
        if (cookie.substring(0, name.length + 1) == (name + '=')) {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
        }
    }
}
return cookieValue;
}

const host = axios.create({
  baseURL: import.meta.env.VITE_APP_API,
  headers: {
    'X-Custom-Token': initData,
    'X-CSRFToken': getCookie('csrftoken')
  },
})

// Интерцепторы для отладки (временно включены)
host.interceptors.request.use(
  (config) => {
    console.log('API Request:', {
      url: config.url,
      method: config.method,
      headers: config.headers,
      data: config.data
    })
    return config
  },
  (error) => Promise.reject(error)
)

// Смещение между серверным и локальным временем (в миллисекундах)
let serverTimeOffset = 0

host.interceptors.response.use(
  (response) => {
    // Вычисляем смещение серверного времени при каждом ответе
    // Приоритет: server_time из ответа > заголовок Date
    if (response.data?.server_time) {
      const serverTime = new Date(response.data.server_time).getTime()
      const clientTime = Date.now()
      serverTimeOffset = serverTime - clientTime
      console.log('Server time offset updated from response:', serverTimeOffset, 'ms')
    } else {
      const serverDateHeader = response.headers['date']
      if (serverDateHeader) {
        const serverTime = new Date(serverDateHeader).getTime()
        const clientTime = Date.now()
        serverTimeOffset = serverTime - clientTime
        console.log('Server time offset updated from header:', serverTimeOffset, 'ms')
      }
    }
    
    console.log('API Response:', {
      url: response.config.url,
      status: response.status,
      data: response.data
    })
    return response
  },
  (error) => {
    console.error('API Response Error:', {
      url: error.config?.url,
      status: error.response?.status,
      data: error.response?.data,
      message: error.message
    })
    return Promise.reject(error)
  }
)

const tonapi = axios.create({
  baseURL: "https://tonapi.io/v2/",
  headers: {
    'Authorization': 'Bearer AHNKO56KDTDIYGIAAAAKPVWGBLOQ2J4Z6W4ZYIP35GPCI6BSG647XSPXK6YEJHY4MTVHRFA'
  },
})

// AEWHUKRJ7HSUPLYAAAACMXNEUNNESVHFOG34WL5K7V2N26432DQSWNSP3FM2B7G6W4MUHKQ

const toncenter = axios.create({
  baseURL: "https://toncenter.com/api/v3/",
})

// Функция для получения текущего серверного времени
const getServerTime = () => {
  return new Date(Date.now() + serverTimeOffset)
}

export { host, tonapi, toncenter, getServerTime }
