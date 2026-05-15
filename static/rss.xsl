<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" version="5" encoding="UTF-8" indent="yes" omit-xml-declaration="yes"/>
  <xsl:template match="/">
    <html lang="zh-Hant">
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width,initial-scale=1"/>
        <title>RSS · <xsl:value-of select="rss/channel/title"/></title>
        <link rel="stylesheet" href="/style.css"/>
        <style>
          .feed-item { border-top: 1px dashed var(--rule); padding-top: 1.4rem; margin-top: 1.4rem; }
          .feed-item:first-of-type { border-top: none; padding-top: 0; margin-top: 0; }
          .feed-item h2 { margin: 0 0 0.25rem; font-size: 1.25rem; }
          .feed-meta { color: var(--quiet); font-size: 0.88rem; margin: 0 0 0.4rem; }
          .feed-note { color: var(--quiet); font-size: 0.9rem; margin-bottom: 2rem; }
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
            <a href="/about/">關於</a>
          </nav>
        </header>
        <main>
          <h1>RSS</h1>
          <p class="feed-note">這是 RSS feed。把 <code><xsl:value-of select="rss/channel/link"/>rss.xml</code> 貼到 feed reader 訂閱。</p>
          <xsl:for-each select="rss/channel/item">
            <article class="feed-item">
              <h2>
                <a>
                  <xsl:attribute name="href"><xsl:value-of select="link"/></xsl:attribute>
                  <xsl:value-of select="title"/>
                </a>
              </h2>
              <p class="feed-meta"><xsl:value-of select="pubDate"/></p>
              <p><xsl:value-of select="description"/></p>
            </article>
          </xsl:for-each>
        </main>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
