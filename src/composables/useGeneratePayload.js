import { randomBytes } from 'crypto';

export function useGeneratePayload() {
    function generatePayload(ttl = 3600) {
        // Generate 8 random bytes
        const randomBytesArray = new Uint8Array(randomBytes(8));
        
        // Get current timestamp in seconds and add TTL
        const ts = Math.floor(Date.now() / 1000) + ttl;
        
        // Convert timestamp to 8-byte array in big-endian
        const tsBytes = new Uint8Array(8);
        let tsBigInt = BigInt(ts);
        for (let i = 7; i >= 0; i--) {
            tsBytes[i] = Number(tsBigInt & 0xffn);
            tsBigInt >>= 8n;
        }
        
        // Concatenate random bytes and timestamp
        const payload = new Uint8Array([...randomBytesArray, ...tsBytes]);
        
        // Convert to hex string
        return Array.from(payload)
            .map(byte => byte.toString(16).padStart(2, '0'))
            .join('');
    }

    return { generatePayload };
}