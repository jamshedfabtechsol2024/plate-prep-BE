from django.urls import include, path
from rest_framework import routers
from app import views

router = routers.DefaultRouter()
router.register(r"register", views.RegisterAPI, "register")
router.register(r"logout", views.LogoutView, "logout")
router.register(r'tag', views.TagViewSet)
router.register(r'ingredients', views.IngredientViewSet)
router.register(r'step', views.StepViewSet)
router.register(r'starch-preparation', views.StarchPreparationViewSet)
router.register(r'recipe', views.RecipeViewSet)
router.register(r'starch-preparation-steps', views.StarchPreparationStepsViewSet)
router.register(r'design-your-plate', views.DesignYourPlateViewSet)
router.register(r'design-your-plate-steps', views.DesignYourPlateStepsViewSet)
router.register(r'predefined-ingredients', views.PredefinedIngredientsViewSet)
router.register(r'predefined-starch', views.PredefinedStarchViewSet)
router.register(r'predefined-vegetables', views.PredefinedVegetableViewSet)
router.register(r'cooking-deviation-comment', views.CookingDeviationCommentViewSet)
router.register(r'real-time-variable-comment', views.RealTimeVariableCommentViewSet)
router.register(r'recipe-process-audit', views.RecipeProcessAuditViewSet)
router.register(r'rating', views.RatingViewSet)
router.register(r'select-holiday', views.SelectHolidayViewSet)
router.register(r'schedule-dish', views.ScheduleDishViewSet)
router.register(r'task', views.TaskViewSet)
router.register(r'wine', views.WineViewSet)
router.register(r'user-detail',views.UserDetailsViewSet)
router.register(r'admin-dashboard',views.AdminDashboardViewSet, basename='admin-dashboard')
router.register(r'super-admin-dashboard',views.SuperAdminDashboardViewSet, basename='super-admin-dashboard')
router.register(r"audit",views.RecipeProcessAuditViewSet,basename="audit")
router.register(r'forget-password', views.PasswordResetRequestViewSet, basename='forget-password')
router.register(r'forget-password-confirm', views.PasswordResetConfirmViewSet, basename='forget-password-confirm')
router.register(r'message', views.MessageViewSet, basename='Message')
router.register(r'ai-recipe-generation', views.AIRecipeGenerationViewSet, basename='ai-recipe-generation')
router.register(r'wine-pairing', views.WinePairViewSet, basename='wine-pairing')
router.register(r'recipe_wine', views.RecipeWineViewSet, basename='recipe_wine')
router.register(r'video_generation', views.RecipeVideoGenerationViewSet, basename='video_generation')
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'menu-categories', views.MenuCategoriesViewSet, basename='menu-categories')
router.register(r'menu-items', views.MenuItemsViewSet, basename='menu-items')
router.register(r'menu', views.MenuViewSet, basename='menu')
router.register(r'presigned_url', views.GetPresingedUrl, basename="presigned_url")
router.register(r'template-generation', views.TemplateGenerationViewset, basename="template-generation")
router.register(r'menu-templates', views.MenuTemplateViewSet, basename="menu-templates")
router.register(r'access-logs', views.LoginLogViewSet, basename='login-log')
router.register(r"instructional-video", views.InstructionVideoViewSet, basename='instructional-video')
router.register(r'shift-note', views.ShiftNoteViewSet, basename='shift-note')
router.register(r"dictionary-category", views.DictionaryCategoryViewset, basename='dictionary-category')
router.register(r"dictionary-items", views.DictionaryItemsViewset, basename='dictionary-items')
router.register(r'editor-template', views.EditorViewset, basename='editor-template')
router.register(r'editor-image', views.EditorImageViewset, basename='editor-image')


urlpatterns = [
    path("api/", include(router.urls)),
    # path("api/grammar_check/", views.GrammarCheckView.as_view(), name="grammar_check"),
    path('api/spell-check/', views.SpellCheckAPI.as_view(), name='spell-check'),
    path('api/login/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/login/refresh/', views.CustomTokenRefreshView.as_view(), name='token_refresh'),
    path(r"^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$",views.activate,name="activate",),
]
