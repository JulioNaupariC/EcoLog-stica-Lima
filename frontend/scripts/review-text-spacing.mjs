// Executes in the audited page. Findings are candidates for visual inspection,
// not an automatic claim of WCAG conformance.
export function inspectTextSpacing() {
  const lines = []
  const clipped = []
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
  let node
  while ((node = walker.nextNode())) {
    const parent = node.parentElement
    if (!node.textContent.trim() || !parent || parent.closest('script, style, svg, .visually-hidden, [hidden], [inert]')) continue
    const style = getComputedStyle(parent)
    if (style.visibility === 'hidden' || style.display === 'none') continue
    const range = document.createRange()
    range.selectNodeContents(node)
    // The responsive table keeps its semantic header in a 1px clipped box;
    // visible card labels are supplied by td::before. This is intentional.
    let assistiveOnly = false
    for (let ancestor = parent; ancestor && ancestor !== document.body; ancestor = ancestor.parentElement) {
      const css = getComputedStyle(ancestor)
      if (css.clip !== 'auto' && ancestor.getBoundingClientRect().width <= 1) assistiveOnly = true
    }
    if (assistiveOnly) continue
    const rects = [...range.getClientRects()].filter(rect => rect.width > 1 && rect.height > 1)
    const visible = rects.map(rect => ({ left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom }))
    let recordedClip = false
    for (let ancestor = parent; ancestor && ancestor !== document.body; ancestor = ancestor.parentElement) {
      const css = getComputedStyle(ancestor)
      const bounds = ancestor.getBoundingClientRect()
      if (!['hidden', 'clip'].includes(css.overflowX) && !['hidden', 'clip'].includes(css.overflowY)) continue
      if (rects.some(rect =>
        (['hidden', 'clip'].includes(css.overflowX) && (rect.left < bounds.left - 2 || rect.right > bounds.right + 2)) ||
        (['hidden', 'clip'].includes(css.overflowY) && (rect.top < bounds.top - 2 || rect.bottom > bounds.bottom + 2)))) {
        if (!recordedClip) clipped.push({ text: node.textContent.trim(), element: parent.className,
          clippingAncestor: ancestor.className,
          intentionalAccountOrBrand: Boolean(parent.closest('.account-meta, .brand-text')) })
        recordedClip = true
      }
      for (const rect of visible) {
        if (['hidden', 'clip'].includes(css.overflowX)) { rect.left = Math.max(rect.left, bounds.left); rect.right = Math.min(rect.right, bounds.right) }
        if (['hidden', 'clip'].includes(css.overflowY)) { rect.top = Math.max(rect.top, bounds.top); rect.bottom = Math.min(rect.bottom, bounds.bottom) }
      }
    }
    let layer = null
    for (let ancestor = parent; ancestor && ancestor !== document.body; ancestor = ancestor.parentElement) {
      if (['fixed', 'sticky'].includes(getComputedStyle(ancestor).position)) { layer = ancestor; break }
    }
    for (const rect of visible.filter(rect => rect.right > rect.left && rect.bottom > rect.top)) lines.push({ parent, layer, text: node.textContent.trim(), rect })
  }
  const overlaps = []
  for (let i = 0; i < lines.length; i++) {
    for (let j = i + 1; j < lines.length; j++) {
      const a = lines[i], b = lines[j]
      if (a.parent === b.parent || a.parent.contains(b.parent) || b.parent.contains(a.parent)) continue
      const x = Math.min(a.rect.right, b.rect.right) - Math.max(a.rect.left, b.rect.left)
      const y = Math.min(a.rect.bottom, b.rect.bottom) - Math.max(a.rect.top, b.rect.top)
      if (x > 2 && y > 2) overlaps.push({ first: a.text, second: b.text, horizontalPixels: x, verticalPixels: y,
        viewportOverlay: a.layer !== b.layer && Boolean(a.layer || b.layer) })
    }
  }
  return { viewport: innerWidth, scroll: document.documentElement.scrollWidth,
    clipped, overlaps, visibleTextLines: lines.length }
}
