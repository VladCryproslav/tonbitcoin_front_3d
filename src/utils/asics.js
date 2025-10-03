export const getAsicData = (nftAddress, allAsics, asicsSheet, property = 'speed') => {
  const matchedAsic = asicsSheet
    .filter((el) =>
      allAsics?.find(
        (asic) =>
          asic?.a === nftAddress &&
          asic?.n?.split(' ')?.join('')?.toUpperCase()?.includes(el.name?.split(' ')?.join('')),
      ),
    )
    .reduce((longest, current, index, arr) => {
      const longestLength = longest?.name?.length || 0
      const currentLength = current?.name?.length || 0

      if (currentLength === longestLength) {
        return index === arr.length - 1 ? current : longest
      }
      return currentLength > longestLength ? current : longest
    }, null)

  return matchedAsic ? matchedAsic?.[property] : property === 'name' ? 'UNDEFINED' : 0
}

export const getInvestorNav = (rentOut, allAsics, asicsSheet) => {
  const inv_profit = rentOut
    ?.filter((item) => item?.end_date)
    ?.reduce((acc, item) => {
      const speed = getAsicData(item?.nft, allAsics, asicsSheet, 'speed') || 0
      const percentage = item?.owner_percentage ? item.owner_percentage / 100 : 0
      return acc + speed * percentage
    }, 0)

  return inv_profit || 0
}
