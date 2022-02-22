/* Step 3: Extract nodes and edges for the economic recovery whole user journey network,
using the session data retreived in `step_two_extract_page_hits.ipynb`. 

ASSUMPTIONS: 
- The node property `sourcePageSessionHitsAll` is the number of distinct sessions that visit 
  the page path.  
    - A session could have multiple page hits for the same page path. For example:

      -------------------------------------------------
      | SESSION | PAGEPATH | ENTRANCE HIT |  EXIT HIT |
      -------------------------------------------------
      |     1   | /brexit  |      TRUE    |    NULL   | 
      |     1   |     /    |      NULL    |    NULL   |
      |     1   | /brexit  |      NULL    |    TRUE   |
      -------------------------------------------------

      In the above example: 
      - all sessions that visit ‘/brexit’ = 1 
      - all sessions that visit ‘/brexit’ and is an entrance page = 1
      - all sessions that visit ‘/brexit’ and is an exit page = 1 
      - all sessions that visit ‘/brexit’ and is neither an entrance or exit page = 0

      Therefore 1 (entrance hit) + 1 (exit hit) = 2, however all session hits = 1. Because of this 
      discrepancy, if a session has multiple page hits for the same page path, and these hits 
      include both an entrance and an exit hit (such as the above example), then this session is 
      counted as `sourcePageSessionHitsEntranceAndExit`. Sessions that visit a page path once, or 
      multiple times, but these hits only include an entrance hit (not exit), then this session is 
      counted as `sourcePageSessionHitsEntranceOnly`. Sessions that visit a page path once, or 
      multiple times, but these hits only include an exit hit (not entrance), then this session is 
      counted as `sourcePageSessionHitsExitOnly` 

- The edge weight `edgeWeight` is the number of distinct sessions that move between Page A
  and Page B. 

- On the rare occasion, some pagePaths are tagged to a different `documentType`, `bottomLevelTaxon`, 
  or `topLevelTaxon`. While it is not clear why this is the case, it is possible that this is a problem
  with the tracking. This is problematic for further analyses, as pagePaths may have multiple entries. 
  Therefore, we only keep the entry with the highest session hit data. We have chosen the top entry as 
  we are more confident that the tracking is correct, as it is likely that the other entries have very 
  low session counts (less than 10, compared to 3000, for example). Note that therefore the top entry 
  will not have captured the session hits for the other entries, so it is likely that count data is being 
  underestimated. As this happens rarely, we accept this as a caveat to our data. 
  
OUTPUT: 
- Two tables related to the nodes and edges of the network: 
  - `govuk-bigquery-analytics.wuj_network_analysis.nodes_er` 
    - Nodes = `sourcePagePath`
    - Node property = `documentType`
    - Node property = `topLevelTaxons`
    - Node property = `bottomLevelTaxons`
    - Node property = `sourcePageSessionHitsAll`
    - Node property = `sourcePageSessionEntranceOnly`
    - Node property = `sourcePageSessionExitOnly`
    - Node property = `sourcePageSessionEntranceAndExit`
    - Node property = `sessionHits`
  - `govuk-bigquery-analytics.wuj_network_analysis.edges_er`
    - Edges = `sourcePagePath` to `destinationPagePath`
    - Edge weight = `edgeWeight`

REQUIREMENTS: 
- Run `step_one_identify_seed_pages.ipynb` to define seed0 and seed1 pages
- Run `step_two_extract_page_hits.sql` to extract page hits for sessions that visit 
  at least one seed0 or seed1 page
*/ 


-- NODES

-- create table to store nodes 
CREATE OR REPLACE TABLE `govuk-bigquery-analytics.wuj_network_analysis.nodes_er` AS (

-- select all sessions and page hits to be included in the functional network 
WITH page_view_approach AS (
    SELECT
        *
    FROM `govuk-bigquery-analytics.wuj_network_analysis.page_view_approach_er`
),

-- set the source and destination pagePath
source_destination_page_path AS ( 
    SELECT
        sessionId,
        pagePath AS sourcePagePath,
        documentType,
        topLevelTaxons,
        bottomLevelTaxons,
        isEntrance,
        isExit,
        sessionHits,
        LEAD(pagePath) OVER (PARTITION BY sessionId ORDER BY hitNumber) AS destinationPagePath
    FROM page_view_approach
),

-- create a column that defines whether a hit is an entrance and/or exit hit
session_hits AS ( 
    SELECT  
        sessionId,
        sourcePagePath,
        documentType,
        topLevelTaxons,
        bottomLevelTaxons,
        isEntrance,
        isExit,
        sessionHits,
        CASE WHEN (isEntrance AND isExit) THEN 'isEntranceAndExit'
             WHEN (isExit AND isEntrance IS NULL) THEN 'isEntrance'
             WHEN (isEntrance AND isExit IS NULL) THEN 'isExit'
        END AS entranceOrExit
FROM source_destination_page_path
GROUP BY sessionId, sourcePagePath, documentType, topLevelTaxons, bottomLevelTaxons, isEntrance, isExit, sessionHits
),

-- aggregate rows over session, pagePath, document type, top level taxons, and 
-- and bottom level taxons, and identify which sessions have an entrance and/or 
-- exit hit for the pagePath    
session_hits_all AS ( 
    SELECT 
        sessionId,
        sourcePagePath,
        documentType,
        topLevelTaxons,
        bottomLevelTaxons,
        sessionHits,
        STRING_AGG(CAST(entranceOrExit AS STRING)) AS allTypesOfHitsInSession
    FROM session_hits
    GROUP BY sessionId, sourcePagePath, documentType, topLevelTaxons, bottomLevelTaxons, sessionHits
    ORDER BY allTypesOfHitsInSession
),

-- count distinct sessions that visit a pagePath, count distinct sessions that visit
-- a pagePath which are an entrance hit only, count distinct sessions that visit a 
-- pagePath which are an exit hit only, count distinct sessions that visit a pagePath 
-- which are both an entrance and exit hit
pages_with_all_counts AS (
    SELECT 
        sourcePagePath,
        documentType,
        topLevelTaxons,
        bottomLevelTaxons,
        sessionHits,
        COUNT(DISTINCT sessionId) AS sourcePageSessionHitsAll,
        COUNT(DISTINCT (CASE WHEN allTypesOfHitsInSession = 'isEntrance' THEN sessionId ELSE null END) ) AS sourcePageSessionHitsEntranceOnly,
        COUNT(DISTINCT (CASE WHEN allTypesOfHitsInSession = 'isExit' THEN sessionId ELSE null END) ) AS sourcePageSessionHitsExitOnly,
        COUNT(DISTINCT (CASE WHEN STARTS_WITH(allTypesOfHitsInSession, 'isEntranceAndExit') OR STARTS_WITH(allTypesOfHitsInSession, 'isEntrance,') OR STARTS_WITH(allTypesOfHitsInSession, 'isExit,') THEN sessionId ELSE null END) ) AS sourcePageSessionHitsEntranceAndExit
    FROM session_hits_all 
    GROUP BY sourcePagePath, documentType, topLevelTaxons, bottomLevelTaxons, sessionHits
    ORDER BY sourcePageSessionHitsAll DESC
),

-- select the top page path with document type, taxon, and session hit data. This is 
-- because sometimes the tracking for taxons is incorrect, which results in multiple rows
-- for the same page path. 
pages_with_rank AS ( 
    SELECT
        *, 
        ROW_NUMBER() OVER ( PARTITION BY sourcePagePath ORDER BY sourcePagePath, sourcePageSessionHitsAll DESC ) AS rank
    FROM pages_with_all_counts
)

SELECT 
    *
FROM pages_with_rank
WHERE rank = 1

);


-- EDGES 

-- create table to store edges
CREATE OR REPLACE TABLE `govuk-bigquery-analytics.wuj_network_analysis.edges_er` AS (

-- select all sessions and page hits to be included in the functional network 
WITH page_view_approach AS (
    SELECT
        *
    FROM `govuk-bigquery-analytics.wuj_network_analysis.page_view_approach_er`
),

-- set the source and destination pagePath
source_destination_page_path AS ( 
    SELECT
        sessionId,
        pagePath AS sourcePagePath,
        LEAD(pagePath) OVER (PARTITION BY sessionId ORDER BY hitNumber) AS destinationPagePath
    FROM page_view_approach
)

-- count the number of times a user session visits sourcePagePath to destinationPagePath    
SELECT
    sourcePagePath,
    destinationPagePath,
    COUNT(DISTINCT sessionId) AS edgeWeight   
FROM source_destination_page_path
WHERE destinationPagePath IS NOT NULL -- do not calculate for when there is no desination pagePath
    AND sourcePagePath != destinationPagePath -- do not calculate for page refreshes 
GROUP BY sourcePagePath, destinationPagePath
ORDER BY edgeWeight DESC

)