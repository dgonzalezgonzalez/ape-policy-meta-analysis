"""Checks against analytical identities, known benchmarks and observed parser failures."""
import unittest
import numpy as np
from scipy import stats
from meta import tau2_reml, full_meta, egger, weighted_mean
from orientation import orientation, legacy_orientation
from parse_sde import split_row, se_number, tonum, parse_table, pick_primary
from jev_direction import extract_context
from quality_sensitivity import rating_multipliers, rating_sensitivity


class AnalysisChecks(unittest.TestCase):
    def test_rating_multiplier_invariance_ties_and_bound(self):
        mu = np.array([3., 1., 3., 9., 2.])
        w = rating_multipliers(mu, 1.)
        np.testing.assert_allclose(w, [1.6, 1.1, 1.6, 1.9, 1.3])
        np.testing.assert_allclose(w, rating_multipliers(17 + 4 * mu, 1.))
        self.assertEqual(w[0], w[2])
        self.assertGreater(w.min(), 1.)
        self.assertLess(w.max(), 2.)
        order = np.array([4, 2, 0, 1, 3])
        np.testing.assert_allclose(w[order], rating_multipliers(mu[order], 1.))

    def test_tied_ratings_recover_unemphasized_estimates(self):
        y, v = np.array([-.4, .1, .5, .2, -.1]), np.array([.01, .1, .03, .2, .1])
        r, w = rating_sensitivity(y, v, np.ones(5), B=29)
        self.assertAlmostEqual(r['summaries'][0]['estimate'], y.mean())
        self.assertAlmostEqual(r['summaries'][3]['estimate'], full_meta(y, v)['estimate'])
        for base in (0, 3):
            for j in (base + 1, base + 2):
                np.testing.assert_allclose(w[j], w[base])
                self.assertAlmostEqual(r['summaries'][j]['delta_lo'], 0.)
                self.assertAlmostEqual(r['summaries'][j]['delta_hi'], 0.)

    def test_rating_weight_bootstrap_reproducible_and_validates_inputs(self):
        y, v, mu = np.arange(5.), np.ones(5), np.arange(5.)
        a, weights = rating_sensitivity(y, v, mu, B=29, seed=12)
        b, _ = rating_sensitivity(y, v, mu, B=29, seed=12)
        self.assertEqual(a, b)
        np.testing.assert_allclose(weights.sum(axis=1), 1.)
        self.assertGreater(a['summaries'][2]['estimate'], a['summaries'][0]['estimate'])
        with self.assertRaises(ValueError):
            rating_sensitivity(y, np.zeros(5), mu, B=29)

    def test_reml_homoskedastic_analytical_solution(self):
        y = np.array([1., 2., 3., 5., 9.])
        variance = .4
        self.assertAlmostEqual(tau2_reml(y, np.repeat(variance, len(y))), y.var(ddof=1) - variance, places=6)

    def test_reml_translation_invariant(self):
        y, v = np.array([-.2, .1, .7, -.4]), np.array([.1, .2, .3, .05])
        self.assertAlmostEqual(tau2_reml(y, v), tau2_reml(y + 100, v), places=6)

    def test_reml_boundary(self):
        self.assertEqual(tau2_reml(np.ones(5), np.ones(5)), 0)

    def test_modified_hk_equal_variance_matches_t_interval(self):
        y = np.array([-2., -1., 1., 2., 4.])
        r = full_meta(y, np.ones(5) * .01)
        self.assertAlmostEqual(r['estimate'], y.mean(), places=7)
        self.assertAlmostEqual(r['se'], stats.sem(y), places=6)

    def test_equal_weight_se(self):
        y = np.array([-2., -1., 1., 2., 4.])
        self.assertAlmostEqual(weighted_mean(y, np.ones(5))['se'], stats.sem(y), places=10)

    def test_egger_tests_intercept(self):
        precision = np.linspace(1, 30, 100)
        noise = np.random.default_rng(12).normal(0, .05, 100)
        y = (.7 + .2 * precision + noise) / precision
        r = egger(y, 1 / precision ** 2)
        self.assertAlmostEqual(r['intercept'], .7, delta=.03)
        self.assertLess(r['p'], .001)

    def test_no_negation_as_positive(self):
        answers = {k: {'noul': p} for k,p in {'higher_benefits': .1, 'lower_benefits': .1,
                   'direction_ambiguous': .1, 'goal_increase': .1, 'goal_decrease': .1}.items()}
        self.assertEqual(orientation(answers)['sign'], 0)
        answers['higher_benefits']['noul'] = .95
        self.assertEqual(orientation(answers)['sign'], 1)
        answers['direction_ambiguous']['noul'] = .9
        self.assertEqual(orientation(answers)['sign'], 0)

    def test_probability_inversion_regression(self):
        self.assertEqual(legacy_orientation(.99, .01, .01, .01)[0], 1)
        self.assertEqual(legacy_orientation(.01, .99, .99, .01)[0], -1)

    def test_escaped_ampersand_parentheses(self):
        self.assertEqual(len(split_row(r'R\&D & .1 & (.2)')), 3)
        self.assertEqual(se_number('(.2)'), .2)
        self.assertEqual(se_number('-.2'), -.2)
        self.assertEqual(tonum('(.2)'), -.2)

    def test_data_block_and_pooled_panel(self):
        tex = r'''\begin{tabular}{lcccccc}
Outcome & $\hat{\beta}$ & SE & SD(Y) & SDE & SE(SDE) & Classification \\
\multicolumn{7}{l}{Panel A: Pooled} \\
R\&D & .2 & (.1) & 2 & .1 & (.05) & Small positive \\
\end{tabular}
\begin{tabular}{p{10cm}}
Notes: SDE equals beta/SD(Y). These notes are longer than the data block.
Research question: What determines a firm's research and development?
Treatment: Binary treatment. Classification refers to magnitude.
\end{tabular}'''
        result = parse_table(tex)
        row = pick_primary(result['rows'])
        self.assertEqual(row['outcome_label'], 'R&D')
        self.assertEqual(row['sde'], .1)
        self.assertEqual(row['se_sde'], .05)
        self.assertIn('Pooled', row['panel'])

    def test_context_excludes_results_and_numerical_effects(self):
        source = r'''\section{Data}
Employment is measured as a paid job among adult survey respondents. The indicator
equals one when the respondent is employed and zero otherwise.

The estimated effect is 0.123 and its standard error is 0.001. Results are strong.

\input{tables/results}
\section{Results}
Employment increased by 0.456. The SDE is 0.789.
\section{Conclusion}
The findings imply a larger effect.'''
        text, sections = extract_context(source, {'outcome_label':'Employment'})
        self.assertIn('adult survey respondents', text)
        self.assertEqual(sections, ['Data'])
        for forbidden in ('0.123','0.456','0.789','SDE','tables/results'):
            self.assertNotIn(forbidden,text)

    def test_balanced_direction_retains_supported_moderate_case(self):
        answers = {k:{'noul':p} for k,p in {'higher_benefits':.81,'lower_benefits':.42,
            'direction_ambiguous':.69,'goal_increase':.1,'goal_decrease':.1}.items()}
        self.assertEqual(orientation(answers)['sign'],1)
        self.assertEqual(orientation(answers,.20,.60,.60,.40)['sign'],0)

    def test_enforcement_proxy_not_treated_as_underlying_harm(self):
        answers = {k:{'noul':p} for k,p in {'higher_benefits':.06,'lower_benefits':.84,
            'direction_ambiguous':.41,'goal_increase':.1,'goal_decrease':.1,
            'administrative_detection':.95}.items()}
        self.assertEqual(orientation(answers)['sign'],0)
        self.assertEqual(orientation(answers,apply_qualifiers=False)['sign'],-1)
        # A registry-based measure of clear harm need not be discarded merely
        # because the auxiliary reporting question is overinclusive.
        answers['direction_ambiguous']['noul'] = .15
        self.assertEqual(orientation(answers)['sign'],-1)


if __name__ == '__main__':
    unittest.main()
