# Assumptions and caveats log

This log contains a list of assumptions and caveats used in this analysis.

## Definitions

Assumptions are RAG-rated according to the following definitions for quality and
impact[^1]:

[^1]: With thanks to the Home Office Analytical Quality Assurance team for these definitions.

| RAG   | Assumption quality                                                                                                              | Assumption impact                                                                           |
|-------|---------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| Green | Reliable assumption, well understood and/or documented; anything up to a validated & recent set of actual data.                 | Marginal assumptions; their changes have no or limited impact on the outputs.               |
| Amber | Some evidence to support the assumption; may vary from a source with poor methodology to a good source that is a few years old. | Assumptions with a relevant, even if not critical, impact on the outputs.                   |
| Red   | Little evidence to support the assumption; may vary from an opinion to a limited data source with poor methodology.             | Core assumptions of the analysis; the output would be drastically affected by their change. |

## Assumptions associated with the functional graph

## Assumption 1: Seed pages are relevant pages associated with a WUJ. These are normally `topic` or `browse` pages.

* Quality: Green
* Impact: Amber

Topic and browse pages are broad ‘areas’ which hyperlink to other relevant pages. It is therefore likely that relevant pages related to a WUJ will be ‘close’ to these pages, e.g. low number of links between pages. If the WUJ is large, it is likely that we will need a relevant page in each ‘subtopic’ of a WUJ. However we do also expect/need input from departments/domain experts to choose seed pages in a WUJ.

## Assumption 2: Certain document types are not relevant to any WUJ

* Quality: Green
* Impact: Green

We assume that certain document types will not be relevant to WUJs. This is based on: 1) the definition of WUJs, and 2) discussions with the Performance Analysts of the WUJ team. WUJs are complex user journeys that cut across multiple government departments and are usually related to a life event, like starting a business. As such, document types such as ‘news_article’ will not be relevant to a WUJ, as these document types are not related to life events. The Performance Analyst community has also suggested that some document types are not relevant to a WUJ, due to these reasons.

## Assumption 3: Seed pages hyperlink to other pages associated with a WUJ

* Quality: Green
* Impact: Amber

This assumption is similar to one of link analysis: 'If page A and page B are connected by a hyperlink the probability that they are on the same topic is higher than if they are not connected'. Therefore, we assume seed pages are also relevant to WUJs.

## Assumption 4: GOV.UK footer pages are not related to a WUJ

* Quality: Green
* Impact: Green

Footer pages are hyperlinked from seed pages, and therefore will always exist in a list of pages that are hyperlinked from seed pages. However, as these pages have not been embedded by an author, the above assumption is not valid: ‘if page A and page B are connected by a hyperlink the probability that they are on the same topic is higher than if they are not connected’. Therefore, we assume that footer pages are not relevant to the WUJ.

## Assumption 5: Session entrance and exit hit counts may take into consideration multiple page hits

* Quality: Green
* Impact: Green

`sourcePageSessionHitsAll` counts unique sessions per page path and document type.  `sourcePageSessionHitsEntranceOnly`, `sourcePageSessionHitsExitOnly`,  and `sourcePageSessionHitsEntranceAndExit` will take into consideration multiple page hits for the same page path and document type.

For example:
      |      SESSION    |     PAGEPATH     |    ENTRANCE HIT    |  EXIT HIT |
      -----------------------------------------------------------------------
      |       1         |     /brexit      |        TRUE        |    NULL   |
      |       1         |       /          |        NULL        |    NULL   |
      |       1         |     /brexit      |        NULL        |    TRUE   |

In the above example, for page path `/brexit`:
   - `sourcePageSessionHitsAll` = 1
   - `sourcePageSessionHitsEntranceOnly` = 0
   - `sourcePageSessionHitsExitOnly` = 0
   - `sourcePageSessionHitsEntranceAndExit` = 1

If a session has multiple page hits for the same page path, and these hits include both an entrance and an exit hit (such as the above example), then this session is counted as `sourcePageSessionHitsEntranceAndExit`. Sessions that visit a page path once, or multiple times, but these hits only include an entrance hit (not exit), then this session is counted as `sourcePageSessionHitsEntranceOnly`. Sessions that visit a page path once, or multiple times, but these hits only include an exit hit (not entrance), then this session is counted as `sourcePageSessionHitsExitOnly.

This approach has been chosen as otherwise the above example would be counted as:
   - `sourcePageSessionHitsAll` = 1
   - `sourcePageSessionHitsEntranceOnly` = 1
   - `sourcePageSessionHitsExitOnly` = 1
   - `sourcePageSessionHitsEntranceAndExit` = 0
and a discrepancy between counts would ensue: 1 (sessions with an entrance hit) + 1 (sessions with an exit hit) = 2, however all session hits = 1.

## Assumptions associated with biased random walks approach

## Assumption 6: For pages in a WUJ, there exists community structure on the functional graph

* Quality: Green
* Impact: Amber

That is, pages in a WUJ have more edges between them than they do to pages outside the WUJ. We assume there to be more page views for pages that are mostly relevant/important to a WUJ.

## Assumption 7: When initialised at a seed page known to be a member of a WUJ, a random walk spends most of its time traversing a path of pages consisting of pages relevant to the WUJ

* Quality: Green
* Impact: Amber

This is due to assumption 6, because random walks are inclined to become trapped within a community of pages.

## Assumption 8: The biased random walk approach assumes that real users access relevant pages in a WUJ

* Quality: Green
* Impact: Amber

The probability to move from a node (i.e. page) to one of its neighbours is based on the proportion of real user sessions that move from that particular page to its neighbours. However, this approach comes with some caveats. WUJs can span multiple topics and may consist of life events that happen over time (i.e. not happen in one user session, but over multiple sessions, over (potentially) years). The majority of sessions (over 50%) only visit 1 page. Previous work has indicated that taking into account the magnitude of user movements during a random walk does not provide a more accurate output (related links). However, considering the magnitude of user movement was requested by our users (Performance Analysts) and therefore we have included this bias.

## Assumption 9: Random walks spend most of their time traversing paths of pages related to a WU

* Quality: Green
* Impact: Green

Hence, the ranking system works under the assumption that pages that occur more frequently within paths, and occur at least once across multiple paths, are more relevant to a WUJ.
