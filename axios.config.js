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

// Интерцепторы для отладки (можно включить при необходимости)
// host.interceptors.request.use(
//   (config) => {
//     console.log('API Request:', config)
//     return config
//   },
//   (error) => Promise.reject(error)
// )

// host.interceptors.response.use(
//   (response) => {
//     console.log('API Response:', response)
//     return response
//   },
//   (error) => {
//     console.error('API Response Error:', error)
//     return Promise.reject(error)
//   }
// )

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

export { host, tonapi, toncenter}
