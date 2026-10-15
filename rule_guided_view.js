/* Two visible reference panels; fitted paths remain inspectable below. */
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct = (x, digits=1) => (100 * x).toFixed(digits) + '%';
const inspect = (id, word='chol') => '?word=' + encodeURIComponent(word) + '&condition=' + encodeURIComponent(id) + '#word-explorer';

export async function mountRuleGuidedView(host) {
 const response = await fetch('rule_guided_view.json');
 if (!response.ok) { host.hidden = true; return; }
 const d = await response.json();
 const named = r => r.kind === 'previous' ? 'Previous fit' : r.label.replace(/ \(lambda=[^)]+\)$/, '');
 const retained = r => r.optimization?.selected === 'existing_feasible_candidate' ? '<span class="quiet">Previous feasible fit retained</span>' : '';
 const table = rows => '<div class="tablewrap"><table aria-label="Rule-guided optimization comparison"><thead><tr><th>Initialization / allowed routes</th><th class="num">Information<br>penalty</th><th class="num">Average usage<br>mismatch ↓</th><th class="num">All-word<br>information ↑</th><th class="num">Common-word<br>information ↑</th><th class="num">chol value<br>ending as chedy</th><th class="num">shol value<br>ending as shedy</th></tr></thead><tbody>' +
  rows.map(r => '<tr><td><a href="' + inspect(r.id) + '">' + esc(named(r)) + '</a>' + (retained(r) ? '<br>' + retained(r) : '') + '</td><td class="num">' + r.weight + '</td><td class="num">' + pct(r.mean_frequency_mismatch) + '</td><td class="num">' + pct(r.information_retained) + '</td><td class="num">' + pct(r.common_information_retained) + '</td><td class="num">' + pct(r.chol_to_chedy) + '</td><td class="num">' + pct(r.shol_to_shedy) + '</td></tr>').join('') + '</tbody></table></div>';
 const biased = d.models.filter(r => r.kind === 'biased');
 host.innerHTML = '<h3>Does a rule-guided start change the answer?</h3>' +
  '<p>The new starting guesses favor <span class="word-small">chol → cheol → chedy</span> and the parallel <span class="word-small">shol → sheol → shedy</span> route, using existing scheduled rules. The optimizer can move away from those guesses. The initialization-only tests keep the same frequency and information objective.</p>' +
  '<p>A separate restriction keeps initial <span class="word-small">ch</span>, initial <span class="word-small">sh</span>, and other words in three separate groups. <strong>This also forbids deleting or adding the initial ch / sh</strong>, so a neutral spelling cannot provide an indirect crossing. It is a stronger hypothesis than simply forbidding direct ch ↔ sh changes.</p>' +
  table(d.models.filter(r => r.kind !== 'biased')) +
  (biased.length ? '<h4 style="margin:25px 0 8px">What if the family preference stays active during fitting?</h4><p>These rows also preserve initial ch / sh and add a continuing penalty for departing from the family template. The strengths in parentheses weight that extra preference. <strong>This changes the objective and supplies an additional assumption</strong>; it is not an improvement under the original objective. The 50% early / 95% later template rates are hypotheses, not measured historical conversion rates.</p>' + table(biased) : '') +
  '<p class="quiet">Every row uses the same 1b starting counts and the same eight sections. Compare rows with the same information penalty, while keeping any additional family preference in view. The last two columns follow the original value, rather than all usage of the endpoint spelling. Common means at least ten occurrences in 1b. Click a model name to inspect its exact fitted routes below.</p>' +
  '<p class="quiet">These are candidates from bounded local searches, not proven global optima or recovered meanings. An initialized route is a hypothesis supplied to the search. <a href="rule-guided.html">Methods and optimizer status</a> · <a href="rule_guided_view.json">Comparison data</a></p>';
}

export async function mountHistoricalReference(host) {
 const response = await fetch('historical_reference_metrics.json');
 if (!response.ok) { host.hidden = true; return; }
 const d = await response.json(), rows = Object.values(d.families);
 const sources = rows.map(r => {
  const links = r.provenance.source_url.split(' | ');
  return '<a href="' + esc(links[0]) + '">' + esc(r.label) + '</a>';
 }).join(' · ');
 host.innerHTML = '<h3>Reference: how much do real Latin abbreviations obscure?</h3>' +
  '<p>Here the original and abbreviated words are <strong>paired by editors</strong>. We measure how much the abbreviated spelling alone identifies the full word, with no sentence context. These are empirical abbreviation references; the Echo routes are fitted hypotheses across different sections.</p>' +
  '<div class="tablewrap"><table aria-label="Historical abbreviation references"><thead><tr><th>Paired reference corpus</th><th class="num">All-word<br>information</th><th class="num">Common-word<br>information</th><th class="num">Tokens on<br>ambiguous spellings</th><th class="num">Best standalone<br>word-error rate</th><th class="num">Decoded usage<br>mismatch</th></tr></thead><tbody>' +
  rows.map(r => { const m=r.pooled; return '<tr><td>' + esc(r.label) + '<br><span class="quiet">' + m.tokens.toLocaleString() + ' paired words</span></td><td class="num">' + pct(m.information_retained,2) + '</td><td class="num">' + pct(m.common_information_retained,2) + '</td><td class="num">' + pct(m.ambiguous_surface_token_share,2) + '</td><td class="num">' + pct(m.minimum_context_free_token_error,2) + '</td><td class="num">' + pct(m.majority_decoded_lexical_frequency_tv,2) + '</td></tr>'; }).join('') +
  '</tbody></table></div>' +
  '<p class="quiet">Common means at least ten full-word occurrences in that reference corpus. “Ambiguous” counts every token whose abbreviated spelling has multiple expansions. The best standalone decoder always chooses the most frequent expansion; its error can be much smaller than the ambiguous share. Usage mismatch compares that decoded full-word distribution with the true full words.</p>' +
  '<div class="rule"><strong>These percentages do not set an expected Echo frequency mismatch.</strong> Abbreviation and expansion are paired versions of the same text, whose observed channel reproduces the abbreviated frequencies exactly by construction. Echo compares different sections under fixed starting usage. Genre, topic, missing rules, and true frequency change can all affect that separate mismatch.</div>' +
  '<p class="quiet">The table pools witnesses, which can combine different scribal conventions. Supplying witness identity retains ' + pct(Math.min(...rows.map(r=>r.within_witness.information_retained_given_witness)),2) + '–' + pct(Math.max(...rows.map(r=>r.within_witness.information_retained_given_witness)),2) + ' of all-word information across these datasets. These finite samples are in-sample references, not a universal loss rate for medieval writing. Full-word spelling differences also count as different identities.</p>' +
  '<p class="quiet">Sources: ' + sources + '. <a href="historical_reference.html">Historical reference study</a> · <a href="historical_reference_metrics.json">Complete metrics and provenance</a>.</p>';
 const usageResponse = await fetch('historical_reference_vulgate_usage.json');
 if (usageResponse.ok) {
  const u=await usageResponse.json(), n=u.natural_summary, s=u.shuffled_summary;
  host.insertAdjacentHTML('beforeend', '<h4 style="margin:25px 0 8px">A stable vocabulary can still have substantial frequency mismatch</h4>' +
   '<p>For a separate control, the Clementine Vulgate is split into ' + u.chains + ' consecutive chains with the same eight passage lengths as Echo. Every word retains its own spelling and starting value throughout: <strong>all-word and common-word information remain 100%</strong>. Only its observed usage changes between passages.</p>' +
   '<div class="tablewrap"><table aria-label="Vulgate fixed-usage control"><thead><tr><th>Identity-preserving control</th><th class="num">Average usage<br>mismatch</th><th class="num">Common-word usage<br>mismatch, conditional</th><th class="num">Information<br>retained</th></tr></thead><tbody>' +
   [['Natural Vulgate passage order',n],['Same words shuffled: sampling control',s]].map(([label,x]) => '<tr><td>' + label + '</td><td class="num">' + pct(x.mean_tv.mean) + '</td><td class="num">' + pct(x.mean_common_conditional_tv.mean) + '</td><td class="num">100%</td></tr>').join('') +
   '</tbody></table></div><p class="quiet">Mean mismatch averages the seven later passages against the fixed first-passage rates. The common-word column freezes the initial ≥10 cohort and renormalizes within that cohort; it is not the whole-vocabulary score. Shuffling uses three predetermined seeds. Latin vocabulary, morphology, genre and repetition are not matched to Voynich, so this is a descriptive control, not an expected Echo score or a significance threshold. Passage order is not a chronology of language change.</p>' +
   '<p class="quiet">Source: <a href="' + esc(u.provenance.source_url) + '">Clementine Vulgate electronic text</a>, ' + esc(u.provenance.edition) + '. <a href="historical_reference_vulgate_usage.json">All passage spans, metrics and provenance</a>.</p>');
 }
}

