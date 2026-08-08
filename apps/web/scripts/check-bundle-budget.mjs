import { readdir, stat } from "node:fs/promises"

const assetsDir = new URL("../dist/assets/", import.meta.url)
const limits = {
  largestCoreJavaScript: 450 * 1024,
  totalCoreJavaScript: 700 * 1024,
  totalJavaScript: 700 * 1024,
  totalCss: 130 * 1024,
}

const files = await readdir(assetsDir)
const sizes = await Promise.all(
  files.map(async (file) => ({
    file,
    bytes: (await stat(new URL(file, assetsDir))).size,
  }))
)
const javascript = sizes.filter(({ file }) => file.endsWith(".js"))
const coreJavascript = javascript
const css = sizes.filter(({ file }) => file.endsWith(".css"))
const largestCoreJavaScript = Math.max(
  ...coreJavascript.map(({ bytes }) => bytes),
  0
)
const totalCoreJavaScript = coreJavascript.reduce(
  (total, { bytes }) => total + bytes,
  0
)
const totalJavaScript = javascript.reduce(
  (total, { bytes }) => total + bytes,
  0
)
const totalCss = css.reduce((total, { bytes }) => total + bytes, 0)
const metrics = {
  largestCoreJavaScript,
  totalCoreJavaScript,
  totalJavaScript,
  totalCss,
}

for (const [metric, value] of Object.entries(metrics)) {
  const limit = limits[metric]
  if (value > limit) {
    throw new Error(`${metric} is ${value} bytes, above the ${limit}-byte budget`)
  }
}

console.log(
  JSON.stringify({
    ...metrics,
    assetCount: sizes.length,
  })
)
