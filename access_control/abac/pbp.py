from abc import ABC, abstractmethod
from py_abac import PDP
from py_abac.context import EvaluationContext
from py_abac.request import AccessRequest


class AbstractAsyncPDP(PDP, ABC):
    @abstractmethod
    async def is_allowed(self, request: AccessRequest):
        pass


class AsyncPDB(AbstractAsyncPDP):

    async def is_allowed(self, request: AccessRequest):
        """
            Check if authorization request is allowed

            :param request: request object
            :return: True if authorized else False
        """
        if not isinstance(request, AccessRequest):
            raise TypeError("Invalid type '{}' for authorization request.".format(request))

        # Get appropriate evaluation algorithm handler
        evaluate = getattr(self, "_{}".format(self._algorithm))
        # Create evaluation context
        ctx = EvaluationContext(request, self._providers)

        # Get filtered policies based on targets from storage
        policies = self._storage.get_for_target(ctx.subject_id, ctx.resource_id, ctx.action_id)
        # Filter policies based on fit with authorization request
        policies = [policy async for policy in policies if policy.fits(ctx)]

        return evaluate(policies)