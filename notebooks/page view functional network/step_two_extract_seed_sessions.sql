/* Step 2: Retrieve all page hits from sessions that visited at least 1 seed0 or seed1 
page for the economic recovery whole user journey.

ASSUMPTIONS:
- URL parameteres/anchors are removed from the page paths, as we are only interested in the 
  the gov.uk page path. 
- Seed1 pages found in the footer of the page have been removed
- Certain document types have been ignored, see `document_types_to_ignore`
- Session data has been retrieved from a week's worth of data: 20210803 - 20210809
- Only page hits are included 
- Print pages are not included 
- Truncate URLs of 'simple_smart_answer', 'local_transaction', 'special_route', 
  'licence', 'transaction', and 'Extension' document types, e.g. "/claim-tax-refund/y" 
  TO "/claim-tax-refund". This is because we are not interested in the user's reponse, 
  only the page. 

REQUIREMENTS: 
- Run `step_one_identify_seed_pages.ipynb` to define seed0 and seed1 pages
- `seed1_pages` must be manually copied into `SET seed1_pages `
*/ 


-- declare and set variables 
DECLARE start_date STRING DEFAULT "20210803";
DECLARE end_date STRING DEFAULT "20210809";

DECLARE seed0_pages ARRAY<STRING>;
DECLARE seed1_pages ARRAY<STRING>;
DECLARE document_types_to_ignore ARRAY <STRING>;

SET seed0_pages = ['/topic/further-education-skills', 
                   '/browse/working/finding-job'];

SET seed1_pages = ['/browse/working/state-pension',
                   '/browse/working/workplace-personal-pensions',
                   '/browse/working/rights-trade-unions',
                   '/contact-jobcentre-plus',
                   '/jobseekers-allowance',
                   '/browse/working/tax-minimum-wage',
                   '/browse/working/time-off',
                   '/looking-for-work-if-disabled',
                   '/become-apprentice',
                   '/volunteering',
                   '/tell-employer-or-college-about-criminal-record',
                   '/browse/working/finding-job',
                   '/employers-checks-job-applicants',
                   '/browse/working/contract-working-hours',
                   '/browse/working/redundancies-dismissals',
                   '/browse/working/armed-forces',
                   '/apply-apprenticeship',
                   '/find-a-job',
                   '/prove-right-to-work',
                   '/job-offers-your-rights',
                   '/report-problem-criminal-record-certificate',
                   '/criminal-record-check-documents',
                   '/criminal-record-checks-apply-role',
                   '/moving-from-benefits-to-work',
                   '/jobsearch-rights',
                   '/find-internship',
                   '/employment-rights-for-interns',
                   '/topic/further-education-skills/apprenticeships',
                   '/find-traineeship',
                   '/work-reference',
                   '/career-skills-and-training',
                   '/access-to-work',
                   '/request-copy-criminal-record',
                   '/guidance/apply-for-communication-support-at-a-job-interview-if-you-have-a-disability-or-health-condition-access-to-work',
                   '/topic/further-education-skills/vocational-qualifications',
                   '/register-jobs-international-organisations',
                   '/topic/defence-armed-forces/military-recruitment-training-operations',
                   '/topic/further-education-skills/administration',
                   '/topic/further-education-skills/learning-records-service',
                   '/topic/work-careers/government-graduate-schemes',
                   '/topic/work-careers/secondments-with-government'];

SET document_types_to_ignore = ['authored_article',
                                'news_article',
                                'news_story',
                                'press_release',
                                'world_news_story',
                                'utaac_decision',
                                'speech',
                                'case_study',
                                'raib_report',
                                'asylum_support_decision',
                                'policy_paper',
                                'corporate_report',
                                'written_statement',
                                'consultation_outcome',
                                'closed_consultation',
                                'maib_report',
                                'person',
                                'correspondence',
                                'employment_tribunal_decision',
                                'employment_appeal_tribunal_decision',
                                'tax_tribunal_decision',
                                'ministerial_role',
                                'residential_property_tribunal_decision',
                                'cma_case',
                                'completed_transaction'
];

-- create table to store results
CREATE OR REPLACE TABLE `govuk-bigquery-analytics.wuj_network_analysis.page_view_approach_er` AS

-- all page hits during a user session during the time range of interest 
WITH primary_data AS ( 
    SELECT 
        hits.hitNumber,
        REGEXP_REPLACE(hits.page.pagePath, r'[?#].*', '') AS pagePath,
        CONCAT(fullVisitorId, "-", CAST(visitId AS STRING)) AS sessionId,
        (SELECT value FROM hits.customDimensions WHERE index = 2) AS documentType,
        (SELECT value FROM hits.customDimensions WHERE index = 4) AS contentID,
        hits.isEntrance,
        hits.isExit
    FROM `govuk-bigquery-analytics.87773428.ga_sessions_*`
    CROSS JOIN UNNEST(hits) AS hits
    WHERE
        _TABLE_SUFFIX BETWEEN start_date AND end_date
        AND hits.page.pagePath NOT LIKE "/print%"
        AND hits.type = 'PAGE'
),

-- remove irrelevant document types `document_types_to_ignore`
sessions_remove_document_types AS (
    SELECT 
        *
    FROM primary_data
    WHERE documentType NOT IN UNNEST(document_types_to_ignore)
),

-- truncate URLs of certain document types
sessions_truncate_urls AS (
    SELECT * REPLACE (
        CASE
            WHEN documentType IN ('smart_answer', 'simple_smart_answer', 'local_transaction', 'special_route', 'licence', 'transaction', 'Extension')
            THEN REGEXP_EXTRACT(pagePath, "^\\/[^\\/]+")
            ELSE pagePath
        END AS pagePath
    )
    FROM sessions_remove_document_types
),

-- sessions which visit at least one `seed0_pages` or `seed1_pages`
sessions_with_seed_0_or_1 AS (
    SELECT DISTINCT 
        sessionId
    FROM sessions_truncate_urls
    WHERE pagePath IN UNNEST(seed0_pages)
        OR pagePath IN UNNEST(seed1_pages)
    GROUP BY sessionId, pagePath
)

-- all session data (page hits) that visit at least one `seed0_pages` or `seed1_pages`
SELECT 
    sessionId,
    hitNumber,
    pagePath,
    contentID,
    documentType,
    isEntrance,
    isExit
FROM sessions_truncate_urls
WHERE sessionId IN (SELECT sessionId FROM sessions_with_seed_0_or_1)
ORDER BY sessionId, hitNumber