<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" version="5" encoding="UTF-8" indent="yes" omit-xml-declaration="yes"/>
  <xsl:template match="/">
    <html lang="zh-Hant">
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width,initial-scale=1"/>
        <title>RSS Feed · <xsl:value-of select="rss/channel/title"/></title>
        <link rel="stylesheet" href="/style.css"/>
        <style>
          .feed-banner { background: var(--code-bg); border-left: 3px solid var(--accent); padding: 1rem 1.25rem; margin: 1.5rem 0 2.5rem; }
          .feed-url-code { display: block; padding: 0.6rem 0.8rem; background: rgba(0,0,0,0.05); margin-top: 0.5rem; word-break: break-all; font-family: monospace; font-size: 0.92rem; }
          .feed-item { border-top: 1px dashed var(--rule); padding-top: 1.4rem; margin-top: 1.4rem; }
          .feed-item:first-of-type { border-top: none; padding-top: 0; margin-top: 0; }
          .feed-item h3 { margin: 0 0 0.25rem; }
          .feed-meta { color: var(--quiet); font-size: 0.88rem; margin: 0 0 0.4rem; }
        </style>
      </head>
      <body>
        <header class="site-header">
          <div class="site-masthead">
            <a class="site-title" href="/"><xsl:value-of select="rss/channel/title"/></a>
          </div>
          <nav class="site-nav">
            <a href="/">首頁</a>
            <a href="/posts/">文章</a>
            <a href="/blogroll/">部落卷</a>
            <a href="/about/">關於</a>
          </nav>
        </header>
        <main>
          <h1>RSS Feed</h1>
          <p>這是 <em><xsl:value-of select="rss/channel/title"/></em> 的 feed。用 feed reader 訂閱，照作者的節奏接收新文章。</p>

          <div class="feed-banner">
            <strong>Feed 網址（複製這個貼到 feed reader）：</strong>
            <code class="feed-url-code"><xsl:value-of select="rss/channel/link"/>feed.xml</code>
          </div>

          <h2>沒用過 feed reader？</h2>
          <p>Feed reader 把多個 RSS 來源聚在一起讀，介面像 email。常見選擇：<a href="https://netnewswire.com/">NetNewsWire</a>（Mac、開源）、<a href="https://feedly.com/">Feedly</a>（網頁）、<a href="https://www.inoreader.com/">Inoreader</a>（網頁）、<a href="https://miniflux.app/">Miniflux</a>（自架）。挑一個能讓你「打開不被分心」的。</p>

          <h2>最近的文章</h2>
          <xsl:for-each select="rss/channel/item">
            <article class="feed-item">
              <h3>
                <a>
                  <xsl:attribute name="href"><xsl:value-of select="link"/></xsl:attribute>
                  <xsl:value-of select="title"/>
                </a>
              </h3>
              <p class="feed-meta"><xsl:value-of select="pubDate"/></p>
              <p><xsl:value-of select="description"/></p>
            </article>
          </xsl:for-each>
        </main>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
