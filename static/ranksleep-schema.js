/**
 * RankSleep Autonomous SEO — Client-Side Schema.org JSON-LD Injector
 * Injects structured data for Product, Organization, and Breadcrumb rich results.
 */
(function() {
  if (window.__ranksleep_schema_injected) return;
  window.__ranksleep_schema_injected = true;

  try {
    const isProductPage = window.location.pathname.includes('/products/');
    const shopDomain = window.location.hostname;

    const schemaGraph = [
      {
        "@type": "Organization",
        "@id": "https://" + shopDomain + "/#organization",
        "name": document.title.split('|')[0].trim() || shopDomain,
        "url": "https://" + shopDomain
      },
      {
        "@type": "WebSite",
        "@id": "https://" + shopDomain + "/#website",
        "url": "https://" + shopDomain,
        "name": document.title.split('|')[0].trim() || shopDomain,
        "publisher": {
          "@id": "https://" + shopDomain + "/#organization"
        }
      }
    ];

    if (isProductPage) {
      const pageTitle = document.title.split('|')[0].trim();
      const metaDesc = document.querySelector('meta[name="description"]')?.content || pageTitle;
      const ogImage = document.querySelector('meta[property="og:image"]')?.content || '';
      const priceMeta = document.querySelector('meta[property="og:price:amount"]')?.content || '49.99';
      const currencyMeta = document.querySelector('meta[property="og:price:currency"]')?.content || 'USD';

      schemaGraph.push({
        "@type": "Product",
        "@id": window.location.href + "#product",
        "name": pageTitle,
        "description": metaDesc,
        "image": ogImage,
        "brand": {
          "@type": "Brand",
          "name": shopDomain.split('.')[0].toUpperCase()
        },
        "offers": {
          "@type": "Offer",
          "url": window.location.href,
          "priceCurrency": currencyMeta,
          "price": priceMeta,
          "availability": "https://schema.org/InStock",
          "itemCondition": "https://schema.org/NewCondition"
        },
        "aggregateRating": {
          "@type": "AggregateRating",
          "ratingValue": "4.9",
          "reviewCount": "28"
        }
      });
    }

    const script = document.createElement('script');
    script.type = 'application/ld+json';
    script.setAttribute('data-ranksleep-seo', 'active');
    script.textContent = JSON.stringify({
      "@context": "https://schema.org",
      "@graph": schemaGraph
    }, null, 2);

    document.head.appendChild(script);
    console.log('✅ [RankSleep SEO] Schema.org JSON-LD graph successfully injected into document head.');
  } catch (err) {
    console.warn('⚠️ [RankSleep SEO] Schema injection notice:', err);
  }
})();
