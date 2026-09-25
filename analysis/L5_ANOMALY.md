# L4 to L5: baseline-adjusted reanalysis

Raw level means include all domains. Adjusted means use only domains nonconstant at BOTH levels. All differences are proportions (multiply by 100 for percentage points). Bootstrap uses 10,000 domain-stratified IMAGE-cluster resamples; an image receives the same multiplicity at both levels. Empirical ground-truth baselines are held fixed, so CIs are conditional on the evaluated truth distribution. The constant-exclusion difference is descriptive, not a causal attribution.

| model | n | baseline | raw_accuracy | adjusted_score | excluded_constant | small_n | paired_domains | raw_L4 | raw_L5 | adjusted_L4 | adjusted_L5 | n_L4_all | n_L5_all | n_L4_paired | n_L5_paired | baseline_L4_paired | baseline_L5_paired | raw_L4_paired | raw_L5_paired | adjusted_L5_minus_L4 | ci_low | ci_high | verdict | raw_L5_without_constants | raw_rise_before | raw_rise_after | raw_rise_removed_by_constant_exclusion |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude_opus_5 | 3100 | 0.321290 | 0.454839 | 0.183569 | False | False | 31 | 0.402941 | 0.551765 | 0.149082 | 0.218056 | 1700 | 1700 | 1550 | 1550 | 0.245161 | 0.397419 | 0.379355 | 0.530323 | 0.068974 | 0.024170 | 0.113034 | survives | 0.530323 | 0.148824 | 0.127381 | 0.021442 |
| claude_sonnet_5 | 3100 | 0.321290 | 0.327097 | -0.043400 | False | False | 31 | 0.297647 | 0.383529 | 0.008937 | -0.095736 | 1700 | 1700 | 1550 | 1550 | 0.245161 | 0.397419 | 0.285806 | 0.368387 | -0.104672 | -0.157881 | -0.051941 | reverses | 0.368387 | 0.085882 | 0.070740 | 0.015142 |
| deepseek_v4_1_flash | 3100 | 0.321290 | 0.269032 | -0.191828 | False | False | 31 | 0.238824 | 0.348235 | -0.077344 | -0.306313 | 1700 | 1700 | 1550 | 1550 | 0.245161 | 0.397419 | 0.227097 | 0.310968 | -0.228968 | -0.283913 | -0.173435 | reverses | 0.310968 | 0.109412 | 0.072144 | 0.037268 |
| gemini_3_8_flash | 3100 | 0.321290 | 0.484194 | 0.219608 | False | False | 31 | 0.454118 | 0.550000 | 0.220583 | 0.218634 | 1700 | 1700 | 1550 | 1550 | 0.245161 | 0.397419 | 0.430323 | 0.538065 | -0.001949 | -0.049164 | 0.044648 | indistinguishable from zero | 0.538065 | 0.095882 | 0.083947 | 0.011935 |
| gpt_5_6_luna | 3100 | 0.321290 | 0.263226 | -0.169157 | False | False | 31 | 0.238824 | 0.340000 | -0.074246 | -0.264069 | 1700 | 1700 | 1550 | 1550 | 0.245161 | 0.397419 | 0.226452 | 0.300000 | -0.189823 | -0.247751 | -0.131252 | reverses | 0.300000 | 0.101176 | 0.061176 | 0.040000 |
| gpt_5_6_sol | 3100 | 0.321290 | 0.329677 | -0.033398 | False | False | 31 | 0.305882 | 0.404706 | 0.030280 | -0.097077 | 1700 | 1700 | 1550 | 1550 | 0.245161 | 0.397419 | 0.291613 | 0.367742 | -0.127357 | -0.182329 | -0.075919 | reverses | 0.367742 | 0.098824 | 0.061860 | 0.036964 |
| grok_4_6 | 3100 | 0.321290 | 0.372903 | 0.057892 | False | False | 31 | 0.326471 | 0.463529 | 0.080726 | 0.035059 | 1700 | 1700 | 1550 | 1550 | 0.245161 | 0.397419 | 0.311613 | 0.434194 | -0.045667 | -0.091132 | 0.000745 | indistinguishable from zero | 0.434194 | 0.137059 | 0.107723 | 0.029336 |
| inking | 3100 | 0.321290 | 0.247097 | -0.222736 | False | False | 31 | 0.232353 | 0.321176 | -0.079506 | -0.365966 | 1700 | 1700 | 1550 | 1550 | 0.245161 | 0.397419 | 0.210323 | 0.283871 | -0.286461 | -0.343340 | -0.229998 | reverses | 0.283871 | 0.088824 | 0.051518 | 0.037306 |
| muse_glimmer_30b | 3100 | 0.321290 | 0.279677 | -0.194990 | False | False | 31 | 0.258235 | 0.334706 | -0.049386 | -0.340594 | 1700 | 1700 | 1550 | 1550 | 0.245161 | 0.397419 | 0.246452 | 0.312903 | -0.291208 | -0.343732 | -0.239474 | reverses | 0.312903 | 0.076471 | 0.054668 | 0.021803 |
| perplexity_sonar_pro | 3100 | 0.321290 | 0.232258 | -0.215963 | False | False | 31 | 0.207059 | 0.313529 | -0.136017 | -0.295909 | 1700 | 1700 | 1550 | 1550 | 0.245161 | 0.397419 | 0.181935 | 0.282581 | -0.159891 | -0.215411 | -0.106239 | reverses | 0.282581 | 0.106471 | 0.075522 | 0.030949 |

- Claude Opus 5: the adjusted L4-to-L5 rise survives (difference +6.90 pp; 95% CI +2.42 to +11.30 pp).
- Claude Sonnet 5: the adjusted L4-to-L5 rise reverses (difference -10.47 pp; 95% CI -15.79 to -5.19 pp).
- DeepSeek V4.1 Flash: the adjusted L4-to-L5 rise reverses (difference -22.90 pp; 95% CI -28.39 to -17.34 pp).
- Gemini 3.8 Flash: the adjusted L4-to-L5 rise indistinguishable from zero (difference -0.19 pp; 95% CI -4.92 to +4.46 pp).
- GPT-5.6 Luna: the adjusted L4-to-L5 rise reverses (difference -18.98 pp; 95% CI -24.78 to -13.13 pp).
- GPT-5.6 Sol: the adjusted L4-to-L5 rise reverses (difference -12.74 pp; 95% CI -18.23 to -7.59 pp).
- Grok 4.6: the adjusted L4-to-L5 rise indistinguishable from zero (difference -4.57 pp; 95% CI -9.11 to +0.07 pp).
- Inkling: the adjusted L4-to-L5 rise reverses (difference -28.65 pp; 95% CI -34.33 to -23.00 pp).
- Muse Glimmer 30B: the adjusted L4-to-L5 rise reverses (difference -29.12 pp; 95% CI -34.37 to -23.95 pp).
- Perplexity Sonar Pro: the adjusted L4-to-L5 rise reverses (difference -15.99 pp; 95% CI -21.54 to -10.62 pp).
