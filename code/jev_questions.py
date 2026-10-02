"""Literal paper-characteristic questions; outcome direction is defined in jev_enrich."""
import os
from paths import ROOT

Q = {'policy_family': {'type': 'choice',
                   'instructions': 'Which single policy domain best describes the evaluated '
                                   'policy?',
                   'criteria': {'health_human_capital': 'public health, mortality, nutrition, '
                                                        'hospitals, education, childcare, schools.',
                                'labor_income': 'employment, wages, hours worked, unemployment, '
                                                'pensions, social insurance, cash transfers, '
                                                'poverty.',
                                'environment_energy': 'emissions, air or water pollution, energy, '
                                                      'climate, agriculture, forestry, land use.',
                                'taxation_prices': 'excise or income taxes, tariffs, price '
                                                   'subsidies, fees, cost-of-living measures.',
                                'regulation_competition': 'regulation, licensing and permits, '
                                                          'antitrust, competition policy, trade '
                                                          'policy, bans and quotas.',
                                'housing_infrastructure': 'housing, zoning, rent control, '
                                                          'transport, roads, broadband, utilities.',
                                'finance_governance': 'banking, credit, disclosure, accounting '
                                                      'rules, policing, courts, elections, civil '
                                                      'service.',
                                'other': 'None of the listed domains fits better.'}},
 'instrument_type': {'type': 'choice',
                     'instructions': 'Which single mechanism does the policy use to change '
                                     'behaviour?',
                     'criteria': {'price': 'Changes a price: tax, tariff, subsidy, fee, or price '
                                           'cap.',
                                  'quantity_restriction': 'Restricts or rations a quantity: quota, '
                                                          'ban, licence limit, cap on hours or '
                                                          'doses.',
                                  'information': 'Provides information, disclosure, labelling or a '
                                                 'requirement to disclose.',
                                  'direct_transfer': 'Direct transfer of resources to eligible '
                                                     'people or firms.',
                                  'public_provision': 'Changes public provision or eligibility '
                                                      'rules for a public service.',
                                  'infrastructure': 'Changes physical or digital infrastructure or '
                                                    'access to it.',
                                  'enforcement': 'Changes enforcement, monitoring or penalties.',
                                  'other': 'None of the listed mechanisms fits better.'}},
 'policy_intensity': {'type': 'score',
                      'instructions': 'How large and binding is the policy intervention described '
                                      'in the state?',
                      'criteria': ['Symbolic or not yet implemented: the policy is announced, '
                                   'optional, or effectively absent.',
                                   'Small: applies to a narrow group, a small dose, or a short '
                                   'period.',
                                   'Substantial: applies to a broad group or a meaningful dose.',
                                   'Maximum: a sweeping national ban, a large price change, or '
                                   'near-universal coverage.']},
 'target_population': {'type': 'choice',
                       'instructions': 'Which group is the policy aimed at or most directly '
                                       'affects?',
                       'criteria': {'children_youth': 'Children, school-age youth, or students.',
                                    'working_age': 'Working-age adults and their employers.',
                                    'unemployed': 'Jobseekers and the unemployed.',
                                    'elderly_retired': 'Older or retired people, and pensioners.',
                                    'low_income': 'Low-income, means-tested, or otherwise '
                                                  'disadvantaged households.',
                                    'firms_industry': 'Firms, employers, or an industry sector.',
                                    'general_public': 'The population as a whole, with no specific '
                                                      'group targeted.',
                                    'migrants_minority': 'Migrants, refugees, minorities, or a '
                                                         'defined ethnic or religious group.',
                                    'none': 'No affected group can be identified from the '
                                            'information given.'}},
 'design_strength': {'type': 'score',
                     'instructions': 'How credible is the causal identification strategy actually '
                                     'described in the state?',
                     'criteria': ['No credible strategy: only correlations, descriptive '
                                  'differences, or an uncontrolled before/after comparison.',
                                  'Weak: a control-group comparison or a simple '
                                  'difference-in-differences with no evidence on the identifying '
                                  'assumption.',
                                  'Moderate: difference-in-differences or a regression design with '
                                  'a stated, plausible source of exogenous variation and a stated '
                                  'identifying assumption.',
                                  'Strong: a regression discontinuity, instrumental variable, '
                                  'randomised assignment, or a natural experiment with a credible '
                                  'source of variation.',
                                  'Very strong: randomised assignment, or a design whose '
                                  'identifying assumption is directly tested and confirmed in the '
                                  'text.']},
 'uses_random_assignment': {'type': 'noul',
                            'instructions': 'Does the study involve random assignment of the '
                                            'policy to units, for example an experiment or '
                                            'randomised trial?',
                            'criteria': {'true': 'Random assignment or randomisation of treatment '
                                                 'is part of the design.',
                                         'false': 'Treatment is not randomly assigned.'}},
 'selection_on_unobservables': {'type': 'noul',
                                'instructions': 'Is it plausible that units differ on unobservable '
                                                'characteristics that also affect the outcome, '
                                                'such that treated and comparison units are not '
                                                'comparable in levels?',
                                'criteria': {'true': 'Selection on unobservables is a credible '
                                                     'concern for this design.',
                                             'false': 'Selection on unobservables is not a '
                                                      'credible concern here.'}},
 'parallel_trends_tested': {'type': 'noul',
                            'instructions': 'Does the state describe a pre-treatment or placebo '
                                            'test that checks and supports the identifying '
                                            'assumption of the design?',
                            'criteria': {'true': 'A pre-trend, placebo, or other test of the '
                                                 'identifying assumption is described.',
                                         'false': 'No such test is described.'}},
 'few_clusters': {'type': 'noul',
                  'instructions': 'Based on the stated sample, does the analysis rely on a small '
                                  'number of independent clusters, for example fewer than 30 '
                                  'regions, states, firms or localities?',
                  'criteria': {'true': 'Fewer than about 30 independent clusters supply the '
                                       'identifying variation.',
                               'false': 'At least about 30 independent clusters supply the '
                                        'identifying variation.'}},
 'reports_placebo': {'type': 'noul',
                     'instructions': 'Does the state describe a placebo, false, or otherwise '
                                     'falsification test being reported?',
                     'criteria': {'true': 'A placebo or falsification test is reported.',
                                  'false': 'No placebo or falsification test is reported.'}},
 'reports_robustness': {'type': 'noul',
                        'instructions': 'Does the state describe robustness checks, such as '
                                        'alternative specifications, alternative samples, '
                                        'alternative controls, or alternative inference?',
                        'criteria': {'true': 'Robustness checks are reported.',
                                     'false': 'No robustness checks are reported.'}},
 'acknowledges_limitation': {'type': 'noul',
                             'instructions': 'Does the state explicitly acknowledge a limitation, '
                                             'caveat, or threat to the validity of its own '
                                             'results?',
                             'criteria': {'true': 'An explicit limitation or caveat about the '
                                                  "study's own results is stated.",
                                          'false': 'No explicit limitation or caveat about the '
                                                   "study's own results is stated."}},
 'data_source_official': {'type': 'noul',
                          'instructions': 'Is the main data source an official statistical or '
                                          'administrative source, such as a national statistics '
                                          'office, a statistical agency, tax authority, regulator, '
                                          'or official register?',
                          'criteria': {'true': 'The main data come from an official statistical or '
                                               'administrative source.',
                                       'false': 'The main data do not come from an official '
                                                'statistical or administrative source.'}},
 'outcome_domain': {'type': 'choice',
                    'instructions': 'Which single domain does the measured outcome variable belong '
                                    'to?',
                    'criteria': {'labour_market': 'Employment, unemployment, hours, wages, '
                                                  'vacancies, firm births and deaths, '
                                                  'productivity.',
                                 'income_distribution': 'Income, earnings, wealth, poverty, '
                                                        'inequality, benefit receipt and amounts.',
                                 'health': 'Mortality, morbidity, disease, nutrition, mental '
                                           'health, health service use.',
                                 'education': 'Enrolment, attainment, test scores, skills.',
                                 'prices_cost': 'Prices, rents, costs, expenditure, household '
                                                'spending, wages in levels.',
                                 'environment': 'Emissions, pollution concentration, energy use, '
                                                'land cover, weather exposure.',
                                 'crime_safety': 'Crime, arrests, convictions, prison, accidents, '
                                                 'injuries, fatalities.',
                                 'behaviour_compliance': 'Take-up, participation, compliance, '
                                                         'disclosure, application or filing '
                                                         'behaviour.',
                                 'political_attitudinal': 'Votes, party support, trust, '
                                                          'satisfaction, legitimacy, protest.',
                                 'administrative_process': 'Processing time, caseload, '
                                                           'administrative cost, staffing, error '
                                                           'rate.',
                                 'other': 'None of the listed domains fits better.'}},
 'outcome_is_monetary': {'type': 'noul',
                         'instructions': 'Is the measured outcome expressed in currency units or '
                                         'in logs of currency units?',
                         'criteria': {'true': 'The outcome is in money terms.',
                                      'false': 'The outcome is not in money terms.'}},
 'outcome_horizon': {'type': 'choice',
                     'instructions': 'What is the longest time horizon over which the outcome is '
                                     'measured?',
                     'criteria': {'short_run': 'Within one year of the policy taking effect.',
                                  'medium_run': 'One to five years.',
                                  'long_run': 'More than five years.',
                                  'mixed': 'Several horizons are reported and no single one '
                                           'dominates.',
                                  'unclear': 'The horizon cannot be determined from the '
                                             'information given.'}},
 'effect_is_direct': {'type': 'noul',
                      'instructions': 'Is the measured outcome an outcome the policy directly acts '
                                      'on, such as the price, quantity, or eligibility the policy '
                                      'itself changes, rather than a downstream market or '
                                      'general-equilibrium outcome?',
                      'criteria': {'true': 'The outcome is one the policy acts on directly.',
                                   'false': 'The outcome is a downstream market or '
                                            'general-equilibrium consequence.'}}}

def load_key():
    key = os.environ.get('TYPESAFE_API_KEY')
    if not key:
        path = ROOT / '.env'
        if path.exists():
            for line in path.read_text(encoding='utf-8').splitlines():
                if line.strip().startswith('TYPESAFE_API_KEY='):
                    key = line.split('=',1)[1].strip().strip(chr(34)).strip(chr(39))
    if not key:
        raise SystemExit('Set TYPESAFE_API_KEY in the environment or a local .env file.')
    return key
