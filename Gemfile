source "https://rubygems.org"

# Jekyll 4.x, not the github-pages gem. GitHub Pages' classic build pins Jekyll
# 3.9 and an allowlist that excludes custom plugins; this site is built by
# GitHub Actions instead, so it can use current Jekyll and any gem it likes.
gem "jekyll", "~> 4.3"

group :jekyll_plugins do
  gem "jekyll-sitemap"
  gem "jekyll-seo-tag"
end

# Windows and JRuby do not ship the zoneinfo database.
platforms :mingw, :x64_mingw, :mswin, :jruby do
  gem "tzinfo", ">= 1", "< 3"
  gem "tzinfo-data"
end

# Faster directory watching on Windows during `jekyll serve`.
gem "wdm", "~> 0.1", platforms: [:mingw, :x64_mingw, :mswin]

# Ruby 3.4 dropped these from the default gems; harmless before then.
gem "base64"
gem "csv"
gem "logger"
