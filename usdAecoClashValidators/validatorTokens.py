"""Public rule and error tokens."""
KEYWORD = 'UsdAecoClashValidators'
ELEMENTS_CHECKER = 'usdAecoClashValidators:ClashResultWithoutElementsChecker'
UNCERTAINTY_CHECKER = 'usdAecoClashValidators:ClashUncertaintyExceedsToleranceChecker'
STATUS_CHECKER = 'usdAecoClashValidators:ClashStatusUnreviewedChecker'
ROUTE_CHECKER = 'usdAecoClashValidators:ClashRouteDisagreementChecker'
WITHOUT_ELEMENTS = 'ClashResultWithoutElements'
UNCERTAINTY_EXCEEDS_TOLERANCE = 'ClashUncertaintyExceedsTolerance'
STATUS_UNREVIEWED = 'ClashStatusUnreviewed'
ROUTE_DISAGREEMENT = 'ClashRouteDisagreement'
ERROR_NAMES = (WITHOUT_ELEMENTS, UNCERTAINTY_EXCEEDS_TOLERANCE, STATUS_UNREVIEWED, ROUTE_DISAGREEMENT)
