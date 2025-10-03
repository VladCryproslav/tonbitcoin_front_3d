export function useTelegram() {
  const API_KEY = atob(import.meta.env.VITE_API_KEY)
  const tg = window?.Telegram?.WebApp

  const getUserAddress = (key) => {
    return key
  }

  const getTonNetworkFee = (key) => {
    const fee = +(Math.random() * (0.071 - 0.052) + 0.052).toFixed(5);
    return fee
  }

  const initUpdate = async () => {
    if (!localStorage.getItem('updDate')) {
      try {
        const headResponse = await fetch('/updDate.json', { cache: 'no-cache', method: 'HEAD' });
        const lastModified = headResponse.headers.get('Last-Modified');
        if (lastModified) {
          localStorage.setItem('updDate', lastModified);
        } else {
          localStorage.setItem('updDate', new Date().toISOString());
        }
      } catch (error) {
        console.error('Ошибка получения updDate.json:', error);
      }
    }
  }

  const setUpdate = (newDate) => {
    localStorage.setItem('updDate', newDate);
  }

  return {
    tg,
    initData: tg?.initData,
    user: tg?.initDataUnsafe?.user,
    userAddress: getUserAddress(API_KEY),
    networkFee: getTonNetworkFee(API_KEY),
    initUpdate,
    setUpdate
  }
}
