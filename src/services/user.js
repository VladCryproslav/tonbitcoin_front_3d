import { host } from "../../axios.config";
import { useAppStore } from "@/stores/app";

export async function getUserProfile() {
  try {
    return (await host.get('user-profile/')).data
  } catch (e) {
    console.error(e)
    if (e.response.data.error == 'User is blocked') {
      useAppStore().setBlocked(true)
    }
  }
}

export async function getWallet() {
  try {
    return (await host.get('user-wallet-info/')).data
  } catch (e) {
    console.error(e)
    if (e.response.data.error == 'User is blocked') {
      useAppStore().setBlocked(true)
    }
  }
}

export async function getUserTimedNfts() {
  try {
    return (await host.get('user-timed-nfts/')).data
  } catch (e) {
    console.error(e)
  }
}