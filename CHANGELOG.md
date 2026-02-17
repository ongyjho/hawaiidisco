# Changelog

## [0.4.0](https://github.com/ongyjho/hawaiidisco/compare/v0.3.2...v0.4.0) (2026-02-17)


### Features

* invalidate digest cache when bookmarks or articles change ([#33](https://github.com/ongyjho/hawaiidisco/issues/33)) ([#34](https://github.com/ongyjho/hawaiidisco/issues/34)) ([f7c779a](https://github.com/ongyjho/hawaiidisco/commit/f7c779acdac27acfee1340fd0f649aa601c70f75))

## [0.3.2](https://github.com/ongyjho/hawaiidisco/compare/v0.3.1...v0.3.2) (2026-02-17)


### Bug Fixes

* add missing imports in app.py after module decomposition ([#30](https://github.com/ongyjho/hawaiidisco/issues/30)) ([a22bb70](https://github.com/ongyjho/hawaiidisco/commit/a22bb706ee63f9776c3249025e36a146eb3cb554))
* replace --max-tokens with --model for Claude CLI 2.x ([4add307](https://github.com/ongyjho/hawaiidisco/commit/4add30783d097067e946f6b88cf0f7ed83106954))
* replace removed --max-tokens with --model for Claude CLI 2.x ([e023f5a](https://github.com/ongyjho/hawaiidisco/commit/e023f5a8ffd07468cab0cc4ff91462d6bd97c020))
* use notify() instead of StatusBar query in digest Obsidian save ([#31](https://github.com/ongyjho/hawaiidisco/issues/31)) ([1e0ba1c](https://github.com/ongyjho/hawaiidisco/commit/1e0ba1c50e878e622c9105548aaafe6d6b8d36af))

## [0.3.1](https://github.com/ongyjho/hawaiidisco/compare/v0.3.0...v0.3.1) (2026-02-17)


### Miscellaneous

* **main:** release 0.3.0 ([0f44178](https://github.com/ongyjho/hawaiidisco/commit/0f441786d2eae53c62d22216a2fda31db85252c5))

## [0.3.0](https://github.com/ongyjho/hawaiidisco/compare/v0.2.4...v0.3.0) (2026-02-17)


### Features

* add --setup-obsidian interactive CLI wizard ([5b59ae0](https://github.com/ongyjho/hawaiidisco/commit/5b59ae078448d5dc4ab3813757c2b19d5cc9cbfc))
* add mark read/unread and mark all read actions ([505d26b](https://github.com/ongyjho/hawaiidisco/commit/505d26bf8b268e6e1e2704b964d71d371a4159de))
* add mark read/unread and mark all read actions ([dfb1108](https://github.com/ongyjho/hawaiidisco/commit/dfb1108256d594d16199fe60221b7aeb696847f1))
* add persona-based personalized insights ([c3caf8f](https://github.com/ongyjho/hawaiidisco/commit/c3caf8fc9251f8ed53a402006058dd22cb938b6c))
* add unread filter and DB query performance indexes ([be3e0f4](https://github.com/ongyjho/hawaiidisco/commit/be3e0f4ad17381b5e8b2e1ddfa1ed1b5d25aca46))
* add unread filter and DB query performance indexes ([296fbfb](https://github.com/ongyjho/hawaiidisco/commit/296fbfb155f2afc698793f42bdebd4d14996dece))


### Bug Fixes

* increase max_tokens and timeout for long article translation ([da3bb6a](https://github.com/ongyjho/hawaiidisco/commit/da3bb6a9ea6c302a1f1b2458440d561060045b41))


### Documentation

* document generate() timeout and max_tokens params in CLAUDE.md ([9f4aca3](https://github.com/ongyjho/hawaiidisco/commit/9f4aca3b20cbc59d0ddfbc03bccfc7728d805a40))
* update README for v0.2.3 with integrations ([86b2aa5](https://github.com/ongyjho/hawaiidisco/commit/86b2aa56c77896983a7e2befa781d9a9eb62ae75))
* update README for v0.2.3 with Obsidian/Notion integration guides ([4d8f5da](https://github.com/ongyjho/hawaiidisco/commit/4d8f5da8093af886b1bc33943fd873c50d55d1c7))


### Miscellaneous

* translate all Korean comments and docstrings to English ([0e43f69](https://github.com/ongyjho/hawaiidisco/commit/0e43f699ce48146f0dab1bcde7845fd69e75a1e0))

## [0.2.4](https://github.com/ongyjho/hawaiidisco/compare/v0.2.3...v0.2.4) (2026-02-17)


### Bug Fixes

* guard all worker-thread query_one calls against NoMatches ([a13126c](https://github.com/ongyjho/hawaiidisco/commit/a13126c2b9504831ce79fd3a109db2cec245c53b))
* guard query_one calls against NoMatches crash ([b802b7d](https://github.com/ongyjho/hawaiidisco/commit/b802b7d1ddf0bd47fc8766f1400a1e5488f6b949))

## [0.2.3](https://github.com/ongyjho/hawaiidisco/compare/v0.2.2...v0.2.3) (2026-02-17)


### Bug Fixes

* guard DetailView queries against NoMatches during mount race ([8a19321](https://github.com/ongyjho/hawaiidisco/commit/8a19321d575d3f4a1d9c731f766b9a47beb1585f))


### Documentation

* update README and version for v0.2.2 ([bcc53c7](https://github.com/ongyjho/hawaiidisco/commit/bcc53c7ba3c59a6d895d532b2062db9acdf3688d))
* update README and version for v0.2.2 ([49b4898](https://github.com/ongyjho/hawaiidisco/commit/49b4898a0e1a0975dc14c44dd9caf73e3293782b))

## [0.2.2](https://github.com/ongyjho/hawaiidisco/compare/v0.2.1...v0.2.2) (2026-02-17)


### Bug Fixes

* remove duplicate force-include causing PyPI upload failure ([d70eee3](https://github.com/ongyjho/hawaiidisco/commit/d70eee310daf67601d752741668df4cbb246c5e2))
* remove duplicate force-include causing PyPI upload failure ([fdfd40f](https://github.com/ongyjho/hawaiidisco/commit/fdfd40f620ceb44d578f0eb94a4e888b155427d7))


### Miscellaneous

* **main:** release 0.2.1 ([4af5d53](https://github.com/ongyjho/hawaiidisco/commit/4af5d53310b3661553f27b1ca4942a9fda3c6a62))
* **main:** release 0.2.1 ([c918e89](https://github.com/ongyjho/hawaiidisco/commit/c918e896d374c01b097fa422f25762603040ab35))

## [0.2.1](https://github.com/ongyjho/hawaiidisco/compare/v0.2.0...v0.2.1) (2026-02-17)


### Bug Fixes

* remove duplicate force-include causing PyPI upload failure ([d70eee3](https://github.com/ongyjho/hawaiidisco/commit/d70eee310daf67601d752741668df4cbb246c5e2))
* remove duplicate force-include causing PyPI upload failure ([fdfd40f](https://github.com/ongyjho/hawaiidisco/commit/fdfd40f620ceb44d578f0eb94a4e888b155427d7))

## [0.2.0](https://github.com/ongyjho/hawaiidisco/compare/v0.1.0...v0.2.0) (2026-02-17)


### Features

* add emoji reactions to [@review](https://github.com/review) comments ([761aeec](https://github.com/ongyjho/hawaiidisco/commit/761aeecb6c733d8860da5fce47477f03ece4b5d6))
* add Obsidian vault integration for bookmarked articles ([2fd32fb](https://github.com/ongyjho/hawaiidisco/commit/2fd32fb2fdc22de5e936a583a7bc3409a63af8c8))
* add Obsidian vault integration for bookmarked articles ([ce422ed](https://github.com/ongyjho/hawaiidisco/commit/ce422ed11a51215233f69f1a81d4303a477312e0))
* add verdict badge (approve/request_changes) to review comments ([036ba31](https://github.com/ongyjho/hawaiidisco/commit/036ba3163f5b96ba7c5d256e3af5e0b972de4063))
* auto-create GitHub issues from AI review suggestions ([895d882](https://github.com/ongyjho/hawaiidisco/commit/895d88249418a69708b417e8a4b192e1ab4c7faa))
* auto-create GitHub issues from AI review suggestions ([6ea011d](https://github.com/ongyjho/hawaiidisco/commit/6ea011dc76e70fbf01e3fcf48d889f43650c4cf9))
* expand i18n to 6 languages (EN/KO/JA/ZH-CN/ES/DE) ([a587686](https://github.com/ongyjho/hawaiidisco/commit/a58768637209db042387d003fc2cba5484267dd0))
* expand i18n to 6 languages with YAML-based locale system ([580d7ad](https://github.com/ongyjho/hawaiidisco/commit/580d7adefac724defccb3adfd04bd273abb94d26))


### Bug Fixes

* skip PR review gracefully when OPENAI_API_KEY is not set ([43b013d](https://github.com/ongyjho/hawaiidisco/commit/43b013d1271ccfb2222457ee2a06c6f70d4e0ff8))


### Miscellaneous

* switch all review output and prompts to English ([3f95cdd](https://github.com/ongyjho/hawaiidisco/commit/3f95cdd729893914939246472746b5320a614dc0))
