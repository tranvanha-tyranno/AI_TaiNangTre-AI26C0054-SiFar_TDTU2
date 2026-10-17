"""Reviewed, reusable procedures. No question IDs, workbook names or answers.

Log mining may activate these lessons, but cannot turn arbitrary log text into
instructions. Add new failure families here after inspecting their evidence.
"""

LESSONS = {
    'json_plan_arrays': {
        'question': r'percent(?:age)? (?:change|decrease|increase|of)|phần trăm so với|퍼센트.*감소|감소.*퍼센트|\bdigit|chữ số|\bcode\b',
        'error': r'JSON|Extra data|Expecting property|container|operator.*array|arity|Expression must have one key',
        'guidance': 'Rebuild malformed plans from the tool schema instead of copying malformed JSON. steps must be an actual JSON array, never a string containing JSON. Each expression has exactly one key; every operator takes an array of expression objects, including unary number/trim/is_number. Wrap constants as value objects. Return one complete object without trailing data. Do not invent operators or recover semantics by editing arbitrary brackets.',
    },
    'tuple_grounding': {
        'question': r'answer as|who spends more|sheet name,\s*(?:integer|value)|group,\s*(?:difference|value)|year,\s*(?:decrease|change|difference)|nhóm.*chênh lệch',
        'error': r'requires 2 final|record fields must depend|Row output requires columns',
        'contract': ('tuple',),
        'guidance': 'For a label-and-value answer, keep both fields in one computed row and output both in the requested order. For row datasets use derive -> sort -> take -> output columns. For scalar comparisons use record with numeric refs and a label from a source cell or an if conditioned on source refs. A bare literal group name is not grounded. collect of numbers does not associate those values with separate labels. Apply numeric formatting only to numeric fields.',
    },
    'row_scalar_refs': {
        'question': r'previous year|preceding year|year, decrease|năm trước',
        'error': r'Scalar reference does not exist|ref only names|Unknown output column',
        'guidance': 'read/filter/derive/sort/take/collect return row datasets. Their fields are accessed with col in descendants, never fabricated refs such as result_E. cell/aggregate/calculate return scalars accessed with ref. To output a selected year and derived change, output those two existing columns from the selected row. To associate scalar labels and metrics, create one record per pair, concat records, then sort/take; separate collect datasets do not create a label column.',
    },
    'section_identity': {
        'question': r'which (?:industry|group|sector)|industry name|group name|tên ngành|nhóm nào',
        'error': r'section heading|repeated detail|source label|NAME/label',
        'guidance': 'Distinguish the entity being ranked from a repeated detail/filter label. A size class or activity repeated under each industry is not the industry name. Inspect section_labels and section_row anchors, filter the requested detail and valid metric, then rank and output the verified _section or actual group-heading cell. Preserve section context before filtering; do not output the constant filter label or guess section boundaries.',
    },
    'conditional_count': {
        'question': r'how many(?! (?:more|hours|thousand|percent))|\bcount\b|bao nhiêu (?:người|dòng|năm|mục)|combien de (?:personnes|lignes|années)|何年|多少(?!个?百分点)|몇(?!.*퍼센트)',
        'error': r'got bool|including False|count counts|conditional count',
        'contract': ('count',),
        'guidance': 'Conditional count is read -> filter(condition) -> aggregate count without expr. count with a boolean expr counts every non-null value, including False. If a boolean was derived, filter it to True before counting. For annual-only questions, identify year-labelled rows and exclude quarters/notes before comparison. Bind the requested metric columns from their full headers. For N-digit codes use length(trim(code)) equal to the requested N and preserve leading zeros.',
    },
    'numeric_text': {
        'question': r'revenue|dollars|currency|doanh thu|millions|higher.*sheet|sheet.*higher',
        'error': r'comparison logic|numeric text|numeric separator|Non-numeric|Expected a number',
        'guidance': 'Spreadsheet amounts may be text with thousands separators or accounting negatives. Convert operands explicitly with number before ordering or comparing numeric metrics; lexicographic comparison gives wrong winners. Keep identifiers and labels as text, especially leading-zero codes. Check numeric validity before arithmetic; do not replace missing observations with zero. Return the requested unit and formatting after computing.',
    },
    'chronological_change': {
        'question': r'previous year|preceding year|fall the most|largest (?:drop|decrease)|năm trước',
        'error': r'lag|prior values|previous row',
        'guidance': 'For changes between years, select annual observations with numeric years and metrics, sort year ascending, then use the lag STEP on the metric. Filter missing prior values before deriving current-minus-prior. Rank decreases by that signed change, then derive a positive decrease magnitude if requested. Return the selected year and computed magnitude together. Do not hard-code the row of a candidate year or use sibling-derived columns.',
    },
    'difference_direction': {
        'question': r'difference|gap|lower than|how much lower|chênh lệch|thấp hơn|écart|plus élevée.*plus faible|低多少|高多少|差|감소|decreas|giảm',
        'error': r'difference.*(?:missing|operation)|percent decrease',
        'contract': ('difference', 'percent_change'),
        'guidance': 'Translate the comparison and requested sign before planning. A gap between highest and lowest is max-minus-min. How much A is lower than B asks B-minus-A, a positive shortfall; signed A-minus-B is a different request. Percent decrease is (old-new)/old*100; percentage-point differences subtract rates without dividing. Compute the requested difference through tools and output that result, not either source cell or the list of observations. Follow requested decimal places in every language.',
    },
    'rowwise_extremum': {
        'question': r'(?:highest|largest|cao nhất|plus élevé|最大).*(?:combined|sum|tổng)|(?:combined|sum|tổng).*(?:highest|largest|cao nhất)|unmet|partially met|chưa được đáp ứng',
        'error': r'rowwise|aggregation axis|excluded.*row',
        'guidance': 'Separate within-category arithmetic from ranking across categories. For the highest combined value, exclude explicitly forbidden summary rows first, derive the sum of requested metrics on EACH remaining category row, then take max or sort/take. Summing each column across all categories and adding those totals answers a different question. Keep requested exclusions during repair even after fixing missing-cell errors.',
    },
    'ratio_computation': {
        'question': r'ratio|as a percentage of|bao nhiêu phần trăm so với|tỷ (?:lệ|số)|比率|占.*百分',
        'error': r'ratio.*(?:missing|operation)|division by zero',
        'guidance': 'A ratio of A to B requires computed A/B, not outputting the numerator or denominator cell. Read both matching metric/period cells, convert numeric text, then calculate div with scalar refs. Multiply by 100 only when a percentage is requested. Check the denominator is nonzero and preserve the requested decimals. Ensure the FINAL output depends on the division, rather than an unused computation elsewhere in the plan.',
    },
    'empty_selection': {
        'question': r'(?!)',
        'error': r'Requested rank outside selected rows|empty (?:selection|dataset)|no matching rows',
        'guidance': 'An empty filtered selection is a source/label problem to inspect, not evidence that the requested entity is absent. Check the actual row samples, header, sheet and section. Compare labels after trim/lower when padding/case is incidental; do not translate question terms into invented workbook labels. Recover the full relevant region when the preview omits rows. Keep the original selection criteria and do not bypass the failure by choosing an arbitrary cell.',
    },
    'hierarchical_mean': {
        'question': r'average.*across all|mean.*across all|trung bình.*tất cả|excluding totals|subcategories only',
        'error': r'mean.*scope|total.*mean',
        'guidance': 'For an unqualified mean across all columns in the requested hierarchical scope, include all matching data columns, including group Total columns. If explicitly restricted to subcategories or excluding totals, obey that restriction. Discover columns from headers rather than a fixed count. This mean convention does not allow adding totals and their components in sums. Never silently turn missing cells into zero.',
    },
    'complete_read_scope': {
        'question': r'how many(?! (?:more|hours|thousand|percent))|annual rows|index series|\d+-digit|toàn bộ|bao nhiêu',
        'error': r'Incomplete read scope|omitted.*(?:annual|identifier)|read bounds.*omit',
        'guidance': 'Preview limits and visible row numbers are not table boundaries. Read the FULL region for unbounded counts, then filter actual data rows; never stop at the last visible preview match. For annual series inspect year_axis_profiles: include every year-labelled observation in the selected annual block, exclude quarters and other series by their labels and section, not by a guessed endpoint. For digit-code questions use identifier_profiles to check that candidate codes continue beyond read.end_row. Inspect missing context if the scope remains ambiguous. Retain all filters when repairing bounds.',
    },
    'row_record_input': {
        'question': r'answer as|year,|which group|group name|nhóm nào',
        'error': r'Unknown column.*available columns are \[\]|collect inputs must be scalar|record.*input',
        'guidance': 'record WITHOUT input evaluates scalar refs only and cannot see columns from any prior row dataset. To rename/project selected rows use record with EXPLICIT input naming that dataset, then fields using col. Example: take id=winner,input=ordered,limit=1; record id=answer,input=winner,fields={"year":{"col":"YEAR"},"total":{"col":"TOTAL"}}; output step=answer,columns=[year,total]. Bind YEAR/TOTAL to observed columns. Alternatively output winner columns directly. Never implicitly attach record to the most recent dataset. To combine read datasets use concat, not collect; collect accepts scalars only.',
    },
    'section_argmax': {
        'question': r'which group.*highest|group had the highest|among.*which group|nhóm.*cao nhất',
        'error': r'occupation category label|section label associated|collect inputs must be scalar|record fields must depend|group-name identity',
        'guidance': 'For a metric repeated under named sections, read each relevant section including its heading, filter the target detail row, CONCAT the row datasets, sort the requested numeric metric and take 1. Return its verified _section; shorten with output.aliases only to a label explicitly in the question. This avoids separate scalar-value/label lists and invented literal record fields. If using cell+record instead, read each real section-heading cell and metric cell, record those scalar refs together, concat records, sort and take 1. Do not output the occupation/activity row label or a numeric score when the question asks which group.',
    },
    'sheet_identity': {
        'question': r'which sheet|sheet name',
        'error': r'record fields must depend.*spreadsheet',
        'guidance': 'Sheet names are metadata, not necessarily text inside worksheet cells. For a sheet-and-value comparison, read each relevant metric row, CONCAT the row datasets, derive a numeric metric with number(col), sort and take 1; output [_sheet, numeric_metric] together. This grounds the sheet name through read metadata and the metric through its cell. A literal sheet name in record may fail grounding if it appears nowhere in the cells. Do not use sibling derive datasets as scalar refs; use calculate number(ref) for scalar conversion or derive number(col) for a row dataset.',
    },
    'threshold_semantics': {
        'question': r'\b(?:above|below|over|under|exceed|less than|greater than|more than|strictly|cao hơn|thấp hơn|trên|dưới|vượt)\b|\b(?:>\s*|<\s*)\d',
        'error': r'threshold|strictly|above.*incorrect|below.*incorrect|condition.*(?:wrong|incorrect)',
        'guidance': 'Translate threshold wording to the operator before judging a plan: above/greater than/exceed means gt; below/less than/under means lt; at least means ge; at most means le. Check the actual operands and trace values, not a reviewer paraphrase. For example, gt 12 includes 12.4 and excludes 12.0. Never change a valid predicate merely to satisfy an unsupported review sentence; repair only a concrete contradiction with the question or source evidence.',
    },
    'header_missing_filter': {
        'question': r'largest gap|highest.*rate|quartile|median|size class|employment size|tổng.*dòng|exclude.*total|excluding.*total',
        'error': r'header|section header|non-numeric|missing cell|numeric guards|leading whitespace|row.*contains.*no data',
        'guidance': 'Before arithmetic or ranking over a sectioned table, filter every required numeric operand with is_number and remove explicit total/summary rows and standalone section headings. A label-only header can survive a label ne filter but must not enter derive/sort. Trim labels only for comparison/output formatting while preserving the source cell provenance. Missing/suppressed markers such as (-8-) and dash are absent data, never zero.',
    },
    'review_evidence_consistency': {
        'question': r'(?!)',
        'error': r'Semantic review requests revision|review.*revise|Recheck the question against',
        'guidance': 'Audit the executed dependency chain through filter -> derive -> sort -> take and final output, not only the initial read. Rows present in read but removed by a numeric filter did not participate in arithmetic. Grounds for revision require a specific violated requirement and source/trace evidence. A revise verdict must list concrete issues; do not issue an empty revise or contradict an operator with a paraphrase. Check claims against evidence rather than changing a valid plan to satisfy unsupported feedback. Existing validation and review gates remain authoritative.',
    },
    'final_output_binding': {
        'question': r'(?!)',
        'error': r'Final step does not exist|Row dataset does not exist',
        'guidance': 'Bind output.step and every input to an actual preceding step ID in the completed plan. Row datasets and scalars have different namespaces: read/filter/derive/sort/take/select/concat/record return rows; cell/aggregate/calculate return scalars. Use output.columns for row outputs; a one-field record is still a row dataset. Repair the full dependency chain without inventing missing steps or altering the requested operation, source scope or numeric precision.',
    },
    'horizontal_series_axis': {
        'question': r'annual figures|annual.*highest|year.*highest|highest.*year',
        'error': r'Header label used as row filter|nonnumeric label.*numeric column',
        'guidance': 'In a wide time-series table, sectors or metrics may be COLUMN HEADERS and years the ROW AXIS. A named sector selects its numeric column; do not filter that column equal to its sector-name text. Inspect the multi-row heading and year_axis_profiles. For a highest-year question, read the complete annual block, filter numeric years/metric, sort that metric descending, take one and output the year column. Annual rows may use the second column; quarters must be excluded. For a comparison count, compare the two header-selected columns then count qualifying annual rows. Never infer data values or endpoints from preview samples.',
    },
    'header_column_mapping': {
        'question': r'not-employed.*fathers|full-time.*mothers|employed.*fathers|mothers.*children|hours per day',
        'error': r'column mapping|wrong.*column|header.*column|hardcoded row|leading whitespace|starts_with.*fails',
        'preview_feature': 'hierarchical_columns',
        'guidance': 'Before computing a comparison under hierarchical headers, bind EACH operand to its full header path: measure, demographic group, employment status and period. Similar neighboring columns can share the group but differ in status or measure. Recheck these paths during review even when the row and arithmetic are correct. Choose letters from the current workbook, never from an earlier plan. Select the requested section and trim activity labels before matching; consume that filtered row in derive/record instead of leaving filters disconnected from cell lookups. Compute the winner and absolute difference from the exact requested operands, and output the requested label and precision.',
    },
    'financial_text_numbers': {
        'question': r'\$|dollar|revenue|fund|financial|debt|assets|millions|tài chính|ngân sách|số tiền',
        'error': r'Ambiguous numeric separators|Non-numeric|currency|accounting|parenthes|parse_number|wrong.*period|end.?of.?period',
        'guidance': 'Financial exports may store amounts as text with currency symbols, thousands separators, decimal points, or accounting negatives in parentheses. Identify the exact period and metric header before parsing; use explicit numeric conversion for every operand and preserve signs. Do not compare formatted strings, drop digits after commas, treat parentheses as labels, or mix end-of-period with average-period rows. After arithmetic, format the requested decimals/commas exactly. When joining sheets, keep source prefixes and aggregate the correct metric column rather than a similarly named total.',
    },
}
