/* Step 3: Extract nodes and edges for the economic recovery whole user journey network,
using the session data retreived in `step_two_extract_page_hits.ipynb`. 

ASSUMPTIONS: 
- The node property `sourcePageSessionHits` is the number of distinct sessions that visit 
  the page path.  
- The edge weight `edgeWeight` is the number of distinct sessions that move between Page A
  and Page B. 

OUTPUT: 
- Two tables related to the nodes and edges of the network: 
  - `govuk-bigquery-analytics.wuj_network_analysis.nodes_er` 
    - Nodes = `sourcePagePath`
    - Node property = `sourcePageSessionHits`
  - `govuk-bigquery-analytics.wuj_network_analysis.edges_er`
    - Edges = `sourcePagePath` to `destinationPagePath`
    - Edge weight = `edgeWeight`

REQUIREMENTS: 
- Run `step_one_identify_seed_pages.ipynb` to define seed0 and seed1 pages
- Run `step_two_extract_page_hits.ipynb` to extract page hits for sessions that visit 
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
        LEAD(pagePath) OVER (PARTITION BY sessionId ORDER BY hitNumber) AS destinationPagePath
    FROM page_view_approach
)

-- Number of session hits for sourcePagePath 
SELECT
    sourcePagePath,
    COUNT(DISTINCT sessionId) AS sourcePageSessionHits
FROM source_destination_page_path
    WHERE sourcePagePath != '/transition' -- this redirects to /brexit
GROUP BY sourcePagePath 
ORDER BY sourcePageSessionHits DESC

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