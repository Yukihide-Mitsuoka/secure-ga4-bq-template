# Changelog

## [2.3.0](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/compare/v2.2.0...v2.3.0) (2026-07-23)


### Features

* **inspection:** add structured promotion catalog ([#238](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/238)) ([7bcf6e2](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/7bcf6e207089c194b6bb60abb4f938f0eac64b5a))

## [2.2.0](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/compare/v2.1.0...v2.2.0) (2026-07-23)


### Features

* **infra:** add opt-in BigQuery column masking ([#233](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/233)) ([7db0ba4](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/7db0ba4698873a7d7bd126d2f7e08e9bad724b13))

## [2.1.0](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/compare/v2.0.1...v2.1.0) (2026-07-22)


### Features

* **inspection:** export deterministic findings CSV ([#229](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/229)) ([5cecba2](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/5cecba2fcaa350a722510726571a205c551ab9c2))


### Bug Fixes

* **inspection:** avoid overstating zero-finding coverage ([#231](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/231)) ([5786c1b](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/5786c1b7e1fcdba0eafb3b45d1d8b036c028b63d))
* **sync:** keep PR body inside workflow script ([#222](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/222)) ([ea2aee4](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/ea2aee4939b792f3ecf2a0317a6213af0a84faab))

## [2.0.1](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/compare/v2.0.0...v2.0.1) (2026-07-22)


### Bug Fixes

* **governance:** adopt ruleset-only discovery ([#220](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/220)) ([bccadec](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/bccadecccc8c862878a845259b47c68b4edc997f))
* **sync:** adopt safe parent propagation ([#217](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/217)) ([3c1c282](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/3c1c28264d07e6f601493d8d65fd45d487d68597))
* **sync:** validate the actual child contract ([#219](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/219)) ([68161a6](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/68161a6d510c0c5d3ba9a03e3ba0618dcbf5acd1))

## [2.0.0](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/compare/v1.8.0...v2.0.0) (2026-07-19)


### ⚠ BREAKING CHANGES

* **governance:** inherit setup policy wrapper ([#190](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/190))

### Features

* **governance:** adapt collaboration read path ([#186](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/186)) ([3a3e839](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/3a3e8396ebc2f4d3e51e54812a7340b7d88b7de2)), closes [#104](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/104)
* **governance:** apply collaboration settings safely ([#188](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/188)) ([a730e8d](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/a730e8dd867aa2c68c3197fd1f07bdafaed7552b))
* **governance:** inherit profile chain resolution ([#197](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/197)) ([7de44e7](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/7de44e7d2e2979be4d178573487555f35d5b0fc6))
* **governance:** inherit setup policy wrapper ([#190](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/190)) ([5b998a8](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/5b998a8e58172ac5d9925eba2a96e6f328d5304e))
* **governance:** inherit solo defaults ([#193](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/193)) ([a0e8993](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/a0e899343a12da3e51580b9c75da6f38070f8228))
* **governance:** inherit Terraform profile ([#200](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/200)) ([7244d94](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/7244d9452d5dc008b831007f3fd0d0d280826999))

## [1.8.0](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/compare/v1.7.0...v1.8.0) (2026-07-18)


### Features

* **governance:** enforce vulnerability intake policy ([#181](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/181)) ([299db56](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/299db565ac60f0ac56c6d57cd3a6f0f88e93b82a)), closes [#178](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/178)
* **governance:** prepare vulnerability intake transport ([#179](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/179)) ([dbc1748](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/dbc17484a6754d5084acfcf7dbc283f23ce0a506)), closes [#178](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/178)

## [1.7.0](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/compare/v1.6.0...v1.7.0) (2026-07-18)


### Features

* **governance:** expose confirmed local apply ([#172](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/172)) ([451c3c2](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/451c3c274b52976bbe455380b7abcee7212ecd98)), closes [#171](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/171)

## [1.6.0](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/compare/v1.5.0...v1.6.0) (2026-07-17)


### Features

* **governance:** restrict internal write transport ([#162](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/162)) ([ece5f40](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/ece5f40d1db6ea28c028bc5afa3c0dffc3f9aae7)), closes [#161](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/161)
* **governance:** verify internal apply execution ([#164](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/164)) ([f5dfdce](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/f5dfdcefe0027f8c67da43c59959a73eace48bd5)), closes [#161](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/161)

## [1.5.0](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/compare/v1.4.0...v1.5.0) (2026-07-17)


### Features

* **governance:** discover Ruleset update constraints ([#154](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/154)) ([5eaa621](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/5eaa621839d0dfb15b76bb67dc2e850fd5bc8b54)), closes [#153](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/153)
* **governance:** plan safe managed Ruleset updates ([#156](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/156)) ([9d9c3de](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/9d9c3de75ea98b957b231b5efe986d4767fe7b8d)), closes [#153](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/153)

## [1.4.0](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/compare/v1.3.0...v1.4.0) (2026-07-17)


### Features

* **governance:** add deterministic comparison ([#136](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/136)) ([1ebe8f5](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/1ebe8f513c433a6c2256c7c29ffbeb2a7678c1d0)), closes [#135](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/135)
* **governance:** add GET-only plan and audit ([#141](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/141)) ([3738733](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/37387333774b0d63d3f8d95286f3ede708677ed1)), closes [#140](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/140)
* **governance:** add pure apply-action planning ([#148](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/148)) ([4df83eb](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/4df83ebe72b8831be19c568e033aa10d14952338)), closes [#146](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/146)
* **governance:** discover repository-owned rulesets ([#147](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/147)) ([b0507da](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/b0507da45f6d877298409c090e9058f9ada9c646)), closes [#146](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/146)

## [1.3.0](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/compare/v1.2.0...v1.3.0) (2026-07-16)


### Features

* **governance:** add GET-only discovery boundary ([#132](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/132)) ([64bd8f6](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/64bd8f67f7cc62765b3fffb5bb675e4664a016b3)), closes [#131](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/131)
* **governance:** add offline policy resolver ([#129](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/129)) ([ab2ff3e](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/ab2ff3edc5b86b2c631d6214a7f28db8e35f6eb5)), closes [#128](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/128)

## [1.2.0](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/compare/v1.1.0...v1.2.0) (2026-07-16)


### Features

* **inheritance:** add read-only parent planner ([#110](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/110)) ([3592b2b](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/3592b2badc0ad07b81f72710bb9bae13d3f9d1b5))

## [1.1.0](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/compare/v1.0.1...v1.1.0) (2026-07-16)


### Features

* **inheritance:** add offline contract validator ([#109](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/109)) ([28475a7](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/28475a72d7d581e732613b9244c4e1e7e22a86e4)), closes [#104](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/104)
* **inheritance:** bootstrap direct-parent contract ([#107](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/107)) ([269a2a3](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/269a2a3bef1cbf494f9e4270d4f1486a1a43ed77)), closes [#104](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/104)

## [1.0.1](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/compare/v1.0.0...v1.0.1) (2026-07-15)


### Bug Fixes

* **release:** attach SBOM assets explicitly ([#102](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/102)) ([8450d1a](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/8450d1aba531942de8f08e7d336e01717602d03b)), closes [#101](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/101)

## 1.0.0 (2026-07-15)


### Features

* **catalog:** add GA4 sensitivity catalog as overridable data ([#7](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/7)) ([21ed311](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/21ed3116ba7866d865b7136f28ca9d7f6b350110))
* **ci:** add credential-free Dataform cost compile ([#47](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/47)) ([03bbc65](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/03bbc6526dc8fb2f76d4b8aaabe6c066742a33b9))
* **ci:** wire opt-in BigQuery cost gate ([#46](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/46)) ([a1a2c79](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/a1a2c7928b034f03ba90169de8a0b03aaf6328e3))
* **ci:** wire reusable BigQuery inspection ([#43](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/43)) ([f8770fd](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/f8770fd49eb76560b0f9ca92583ccaad928d0ace))
* **infra:** wire dev env with bigquery governance modules ([#5](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/5)) ([3859d70](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/3859d70fa0d91995ef96945b6dfc4b8b1f37c414))
* **infra:** wire WIF with deployer/inspector SA separation ([#12](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/12)) ([eb3c0b8](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/eb3c0b85119ce126fce6f8fe29fcf09de25e50fc))
* **inspection:** add application ports and YAML config repositories ([#24](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/24)) ([7a5d556](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/7a5d5560b99eddbcfe4d6db183c14a06e56fbf4d))
* **inspection:** add domain models — snapshot, catalog, params ([#15](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/15)) ([8c4afca](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/8c4afcac9484a2ee119f4b9bfa952c35c3bf518c))
* **inspection:** add IAM, taxonomy, and logging config adapters ([#26](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/26)) ([ed43773](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/ed43773794c8eb45738fdbb243dfb7f5461b9af5))
* **inspection:** add report writers, the CLI, and make inspect ([#28](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/28)) ([059b8ed](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/059b8ed540a92682da2783b79e431fca74665bc0))
* **inspection:** add the BigQuery metadata adapter and client bootstrap ([#25](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/25)) ([becf14c](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/becf14cd788a3d997457a01ff150e6eaab6720ab))
* **inspection:** add the collection and inspection use cases ([#27](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/27)) ([860371a](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/860371a88023d687375da5d2c5de40b8c86bd770))
* **inspection:** bootstrap uv toolchain and inspection module skeleton ([#14](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/14)) ([d4386e5](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/d4386e5ea90e4864e9e3f63c270194879bcd40ff))
* **inspection:** implement IAM and column-security checkpoints (CHK-01..05) ([#19](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/19)) ([e2b391a](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/e2b391a7b353853f1f12d2b0f2ab9ece4c472693))
* **inspection:** inspect mart descriptions ([#73](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/73)) ([76d72b3](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/76d72b374d0cf0c7b4546a892163661d6480f48f)), closes [#70](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/70)
* **profiles:** add dataform-bigquery engine profile ([#11](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/11)) ([b7e961e](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/b7e961e2441426880597e20cddc221598a533156))
* **profiles:** add dbt-bigquery engine profile with governed skeleton ([#6](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/6)) ([a1c8ef3](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/a1c8ef354a02c8605a401ce456a6113fdaff5efd))
* **release:** make initial preparation operable ([#93](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/93)) ([8dbac6f](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/8dbac6fe64af4d826ca81e6abdc694097bfd3a98)), closes [#92](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/92)
* **reporting:** add deterministic AI report core ([#34](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/34)) ([84d1555](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/84d15551c754e63c9ccb7cb726c9e751cbbea642))
* **reporting:** add remediation recipe registry ([#41](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/41)) ([9613f99](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/9613f99d31e89485008171a88ad24e19125e3f4e))
* **reporting:** generate remediation drafts ([#42](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/42)) ([15039ea](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/15039ea39640e06974b306d7e7df8d1e621655ec))
* **reporting:** promote Vertex AI report CLI to main ([#36](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/36)) ([b9a4316](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/b9a4316d721678cbbf90b5efab842d3dcee5e463))
* **reporting:** support CHK-12 artifacts ([#72](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/72)) ([6fcf899](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/6fcf89980c96495d45e815383d029909d548816b)), closes [#70](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/70)
* **security:** add dedicated cost-gate WIF identity ([#45](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/45)) ([7d1386f](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/7d1386f78b5f42fa30bde66d682b3a642bfc35bb))
* **service-packaging:** add versioned menu profile ([#85](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/85)) ([9efec50](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/9efec500b66f528fd8113a39da3774b652187d4f)), closes [#84](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/84)
* **service-packaging:** evaluate engagement scope ([#88](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/88)) ([f1c6ce6](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/f1c6ce63c74694af0335e04312200495c024710a))
* **service-packaging:** publish qualification artifacts ([#90](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/90)) ([389280f](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/389280f0778cbc083aaaff32a32f11929b15060d))
* **service-packaging:** render inspection menu ([#86](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/86)) ([39194d5](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/39194d50808f58c74bd3644d740ead35f24ce140))
* **verification:** add isolated public GA4 path ([#59](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/59)) ([7e88642](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/7e8864226dd6b55595b522b928140be8cb804cce)), closes [#58](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/58)
* **verification:** FR-8 pseudo-sensitive seed data + live E2E evidence ([#10](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/10)) ([c42066a](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/c42066a959292995cffb3c043d10265864dce02d))


### Bug Fixes

* **ci:** exclude nested lockfiles from PR size ([#48](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/48)) ([003592f](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/003592fd086b9fd1a449399f494dec2b2b7c7cb5))
* **ci:** restore security checks ([#53](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/53)) ([90ffe86](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/90ffe8643e5c4ef3c7bc7461dbed57515643eae4))
* **dataform:** minimize assertion projection ([#66](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/66)) ([f361816](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/f3618167ebfd72b26211a061eeefbfabb1ec9407)), closes [#65](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/65)
* **infra:** make deployer service account ID configurable ([#64](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/64)) ([e5d94dc](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/e5d94dcf91b46a4d945152ce18721aef20f72653)), closes [#63](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/63)
* **inspection:** land audit-logging and cost checkpoints on main (CHK-06..10) ([#22](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/22)) ([57dfe60](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/57dfe600817f9234ae0b5f75d71758c24c58aaf5))
* **inspection:** land CHK-11 and the ALL_CHECKS registry on main ([#23](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/23)) ([840cca5](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/840cca53309432c16ee274029958b38039f10b5e))
* **inspection:** normalize Data Catalog locations ([#68](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/68)) ([3210cb2](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/3210cb2da646f69d7afc7a5b65716004e21d634d)), closes [#67](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/67)
* **profiles:** dbt skeleton lint + policy-tag attachment fixes ([#9](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/9)) ([fd88dd0](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/fd88dd0265eff61ec9c7b961c7283aac3e0f5071))
* **release:** accept generated stable version ([#100](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/100)) ([9735fa9](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/9735fa9a713e13ebc505c8307441b20f3b554f90)), closes [#99](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/99)
* **release:** allow preflight gates before approval ([#96](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/96)) ([8197ed5](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/8197ed5ff2296bca2ca5c48d0cae32250b9ef5f3)), closes [#95](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/95)
* **release:** provision gate toolchains ([#98](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/98)) ([2ff847f](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/2ff847f2dbcd869f64ccd0d537ae33d1be491098)), closes [#97](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/97)
* **security:** harden live cost gate proof ([#51](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/51)) ([8e312fa](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/commit/8e312faa8bd2f3e92de4014f53288f6d38985241)), closes [#50](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/50)
