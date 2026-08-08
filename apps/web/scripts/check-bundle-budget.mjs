import { readdir, stat } from "node:fs/promises"
import { join } from "node:path"

const assetsDir = new URL("../dist/assets/", import.meta.url)
const limits = {
  largestJavaScript: 450 * 1024,
  totalJavaScript: 700 * 1024,
  totalCss: 120 * 1024,
}

const files = await readdir(assetsDir)
const sizes = await Promise.all(
  files.map(async (file) => ({ file, bytes: (await stat(new URL(file, assetsDir))).size }))
)
const javascript = sizes.filter(({ file }) => file.endsWith(".js"))
const css = sizes.filter(({ file }) => file.endsWith(".css"))
const largestJavaScript = Math.max(...javascript.map(({ bytes }) => bytes), 0)
const totalJavaScript = javascript.reduce((total, { bytes }) => total + bytes, 0)
const totalCss = css.reduce((total, { bytes }) => total + bytes, 0)

for (const [metric, value] of Object.entries({ largestJavaScript, totalJavaScript, totalCss })) {
  const limit = limits[metric]
  if (value > limit) {
    throw new Error(`${metric} is ${value} bytes, above the ${limit}-byte budget`)
  }
}

console.log(
  JSON.stringify({ largestJavaScript, totalJavaScript, totalCss, assetCount: sizes.length })
)
