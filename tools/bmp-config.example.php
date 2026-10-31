<?php
/* BioMarket Pulse — server settings for api.php (TEMPLATE)
 * Copy this file to bmp-config.php in the folder ABOVE public_html on Hostinger, then add your key.
 * Edit this file in Hostinger's File Manager. Visitors can never see it (PHP runs, it isn't downloaded).
 */
return [
  // 1) Paste your Anthropic API key between the quotes (create it at console.anthropic.com → API keys).
  'ANTHROPIC_API_KEY' => '',

  // 2) Models. Deep Dive and Ask both use Sonnet 5.5.
  //    To make it nearly free, change either one to 'claude-haiku-5-5'.
  'DEEPDIVE_MODEL' => 'claude-sonnet-5-5',
  'ASK_MODEL'      => 'claude-sonnet-5-5',

  // 3) Spending guardrails (US dollars). When the monthly cap is reached, Deep Dive and Ask pause
  //    until the 1st of next month; the rest of the site keeps working.
  'MONTHLY_BUDGET_USD' => 10,

  // Per-visitor daily limits, and a site-wide hourly ceiling on Claude calls.
  'DEEPDIVES_PER_VISITOR_PER_DAY' => 5,
  'ASKS_PER_VISITOR_PER_DAY'      => 20,
  'CLAUDE_CALLS_PER_HOUR_SITEWIDE'=> 60,

  // How long a finished Deep Dive is reused for the next visitor who asks for the same thing (hours).
  'DEEPDIVE_CACHE_HOURS' => 24,

  // Optional: an NCBI API key raises PubMed's rate limit (free at ncbi.nlm.nih.gov/account). Leave '' if unsure.
  'NCBI_API_KEY' => '',
  'NCBI_EMAIL'   => '',

  // 4) Brazil biologicals registry (free). Register at agroapi.cnptia.embrapa.br, create an application,
  //    subscribe it to AGROFIT v1, then paste its Consumer Key and Consumer Secret here.
  //    Then add a daily cron job in hPanel:  php /home/YOURUSER/domains/biomarketpulse.com/public_html/api.php sync
  'AGROAPI_KEY'    => '',
  'AGROAPI_SECRET' => '',

  // Prices per million tokens, used only to track spend against the cap (Sonnet 5.5 / Haiku 5.5, Oct 2026).
  'PRICES' => [
    'claude-sonnet-5-5' => ['in' => 2.00, 'out' => 10.00, 'cache_read_mult' => 0.05],
    'claude-haiku-5-5'  => ['in' => 0.10, 'out' => 0.50,  'cache_read_mult' => 0.10],
    'claude-opus-5-5'   => ['in' => 4.00, 'out' => 20.00, 'cache_read_mult' => 0.05],
  ],
];
