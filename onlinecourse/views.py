from django.shortcuts import render
from django.http import HttpResponseRedirect
from .models import Course, Enrollment, Question, Choice, Submission
#from .models import Course, Enrollment
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


#@login_required
def submit(request, course_id):
    # Get the current user and the course object
    user = request.user
    course = get_object_or_404(Course, pk=course_id)

    # Get the associated enrollment object
    enrollment = get_object_or_404(Enrollment, user=user, course=course)

    # Create a new submission object referring to the enrollment
    submission = Submission.objects.create(enrollment=enrollment)

    # Collect the selected choices from HTTP request object
    for choice_id in extract_answers(request):
        selected_choice = get_object_or_404(Choice, pk=choice_id)
        submission.choices.add(selected_choice)

    # Redirect to show_exam_result view with the submission id to show the exam result
    return redirect('onlinecourse:show_exam_result', course_id=course.id, submission_id=submission.id)



def extract_answers(request):
    submitted_answers = []
    for key in request.POST:
        if key.startswith('choice'):
            value = request.POST[key]
            choice_id = int(value)
            submitted_answers.append(choice_id)
    return submitted_answers


#@login_required
def show_exam_result(request, course_id, submission_id):
    # Get course and submission based on their ids
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)

    # Get the selected choice ids from the submission record
    selected_ids = submission.choices.values_list('id', flat=True)

    # Initialize total score to 0
    total_score = 0

    # For each question in the course, check if the selected choices are correct or not
    for question in course.question_set.all():
        correct_choices = question.choice_set.filter(is_correct=True).values_list('id', flat=True)
        # If all the correct choices and no incorrect choices are selected for a question, increment total_score
        if set(correct_choices) == set(choice_id for choice_id in selected_ids if Choice.objects.get(id=choice_id).question_id == question.id):
            total_score += 1

    # Add the course, selected_ids, and grade to context for rendering HTML page
    context = {
        'course': course,
        'selected_ids': selected_ids,
        'grade': total_score,
    }

    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)


